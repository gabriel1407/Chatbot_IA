"""
routes/subscription_routes.py

Endpoints de planes y suscripciones.

Públicos:
  GET  /api/subscriptions/plans          — lista planes disponibles

Autenticados (cualquier rol):
  GET  /api/subscriptions/me             — mi suscripción actual
  POST /api/subscriptions/subscribe      — seleccionar un plan
  POST /api/subscriptions/cancel         — dar de baja

Solo admin:
  GET  /api/subscriptions/all            — todas las suscripciones
  POST /api/subscriptions/<id>/activate  — activar suscripción pendiente
"""
from flask import Blueprint, request, jsonify

from core.auth.jwt_middleware import require_jwt, get_current_user

# Helper para validación admin (similar a auth_routes.py)
def _require_admin_role():
    user = get_current_user()
    if user.get("role") != "admin":
        raise APIException("Acceso denegado: Se requiere rol de administrador", 403, "FORBIDDEN")
from core.config.dependencies import DependencyContainer
from core.exceptions.custom_exceptions import APIException
from core.logging.logger import get_app_logger

logger = get_app_logger()
subscription_bp = Blueprint("subscriptions", __name__, url_prefix="/api/subscriptions")

# Aplica JWT a todo el blueprint excepto las rutas públicas
subscription_bp.before_request(require_jwt)

# Rutas de este blueprint que son públicas (sin JWT)
_PUBLIC_SUBSCRIPTION = {"subscriptions.list_plans"}


def _before():
    """before_request ya aplicado via require_jwt en el blueprint."""
    pass


def _get_repo():
    return DependencyContainer.get("SubscriptionRepository")


# ─── GET /api/subscriptions/plans  (público) ────────────────────────────────

@subscription_bp.route("/plans", methods=["GET"])
def list_plans():
    """
    Lista todos los planes de suscripción disponibles.
    No requiere autenticación.

    Response:
        { "ok": true, "plans": [ { "id", "name", "price_usd", ... } ] }
    """
    repo = _get_repo()
    plans = repo.list_plans()
    return jsonify({"ok": True, "plans": plans}), 200


# ─── GET /api/subscriptions/me ──────────────────────────────────────────────

@subscription_bp.route("/me", methods=["GET"])
def my_subscription():
    """
    Retorna la suscripción actual del usuario autenticado.

    Response:
        { "ok": true, "subscription": { ... } }
        { "ok": true, "subscription": null }   ← sin suscripción
    """
    username = get_current_user().get("sub")
    repo = _get_repo()
    sub = repo.get_user_subscription(username)
    return jsonify({"ok": True, "subscription": sub}), 200


# ─── POST /api/subscriptions/subscribe ─────────────────────────────────────

@subscription_bp.route("/subscribe", methods=["POST"])
def subscribe():
    """
    Suscribe al usuario autenticado a un plan.

    Body JSON:
        { "plan_id": 2 }

    Respuesta:
        - Plan Free  → status 'active' (acceso inmediato)
        - Plan pago  → status 'pending' (requiere comprobante de pago)
    """
    data = request.get_json(silent=True) or {}
    plan_id = data.get("plan_id")

    if not plan_id or not isinstance(plan_id, int):
        raise APIException("Se requiere 'plan_id' (entero)", 400, "VALIDATION_ERROR")

    username = get_current_user().get("sub")
    repo = _get_repo()

    # Verificar que el plan existe
    plan = repo.get_plan(plan_id)
    if not plan:
        raise APIException("Plan no encontrado", 404, "NOT_FOUND")

    ok, status = repo.subscribe(username, plan_id)
    if not ok:
        raise APIException(f"Error al suscribir: {status}", 500, "SUBSCRIPTION_ERROR")

    if status == "active":
        msg = f"¡Suscripción al plan '{plan['name']}' activada! Ya tienes acceso completo."
    else:
        msg = (
            f"Solicitud de suscripción al plan '{plan['name']}' registrada. "
            "Por favor sube tu comprobante de pago en /api/subscriptions/payment-proof."
        )

    logger.info(f"[Subscription] '{username}' se suscribió al plan '{plan['name']}' → {status}")
    return jsonify({
        "ok":     True,
        "status": status,
        "plan":   plan,
        "message": msg,
    }), 200 if status == "active" else 202


# ─── POST /api/subscriptions/cancel ─────────────────────────────────────────

@subscription_bp.route("/cancel", methods=["POST"])
def cancel_subscription():
    """Da de baja la suscripción activa del usuario autenticado."""
    username = get_current_user().get("sub")
    repo = _get_repo()
    sub = repo.get_user_subscription(username)
    if not sub or sub["status"] not in ("active", "pending"):
        raise APIException("No tienes una suscripción activa para cancelar", 404, "NOT_FOUND")

    repo.cancel(username)
    logger.info(f"[Subscription] '{username}' canceló su suscripción")
    return jsonify({"ok": True, "message": "Suscripción cancelada correctamente"}), 200


# ─── GET /api/subscriptions/all  (admin) ────────────────────────────────────

@subscription_bp.route("/all", methods=["GET"])
def list_all_subscriptions():
    """Lista todas las suscripciones (solo admin)."""
    require_role("admin")()
    # Retornar paginado en el futuro; por ahora simple lista
    repo = _get_repo()
    # Delegamos al repo directo por ahora
    from sqlalchemy import text
    sql = text("""
        SELECT s.id, s.username, s.status, s.starts_at, s.expires_at, s.created_at,
               p.name as plan_name, p.price_usd
        FROM user_subscriptions s
        JOIN subscription_plans p ON p.id = s.plan_id
        ORDER BY s.created_at DESC
        LIMIT 100
    """)
    try:
        with repo.engine.connect() as conn:
            rows = conn.execute(sql).mappings().all()
        data = [
            {
                "id":         r["id"],
                "username":   r["username"],
                "plan_name":  r["plan_name"],
                "price_usd":  float(r["price_usd"]),
                "status":     r["status"],
                "starts_at":  r["starts_at"].isoformat() if r.get("starts_at") else None,
                "expires_at": r["expires_at"].isoformat() if r.get("expires_at") else None,
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            }
            for r in rows
        ]
        return jsonify({"ok": True, "subscriptions": data, "total": len(data)}), 200
    except Exception as exc:
        raise APIException(f"Error listando suscripciones: {exc}", 500, "SERVER_ERROR")


# ─── POST /api/subscriptions/<id>/activate  (admin) ─────────────────────────

@subscription_bp.route("/<int:sub_id>/activate", methods=["POST"])
def activate_subscription(sub_id: int):
    """Activa una suscripción pendiente. Solo admin."""
    require_role("admin")()
    repo = _get_repo()
    activated = repo.activate(sub_id)
    if not activated:
        raise APIException(
            f"Suscripción #{sub_id} no encontrada o ya estaba activa",
            404, "NOT_FOUND"
        )
    logger.info(f"[Subscription] Admin activó suscripción #{sub_id}")
    return jsonify({"ok": True, "message": f"Suscripción #{sub_id} activada"}), 200


# ─── POST /api/subscriptions/payment-proof ───────────────────────────────────

@subscription_bp.route("/payment-proof", methods=["POST"])
def upload_payment_proof():
    """
    El cliente sube la imagen del comprobante de transferencia bancaria.
    Gemini Vision analiza la imagen y extrae monto, referencia y banco.
    El comprobante queda en estado 'pending' hasta que el admin lo confirme.

    Form-data:
        file     — imagen del comprobante (JPG/PNG/WEBP)
        plan_id  — ID del plan al que quiere suscribirse
    """
    import os
    from werkzeug.utils import secure_filename

    username = get_current_user().get("sub")
    repo     = _get_repo()

    # ── Validar plan ──────────────────────────────────────────────────────────
    plan_id = request.form.get("plan_id", type=int)
    if not plan_id:
        raise APIException("Se requiere 'plan_id' en el form-data", 400, "VALIDATION_ERROR")

    plan = repo.get_plan(plan_id)
    if not plan:
        raise APIException("Plan no encontrado", 404, "NOT_FOUND")

    # ── Validar archivo ───────────────────────────────────────────────────────
    if "file" not in request.files:
        raise APIException("Se requiere el campo 'file' con la imagen del comprobante", 400, "VALIDATION_ERROR")

    file = request.files["file"]
    if not file.filename:
        raise APIException("El archivo está vacío", 400, "VALIDATION_ERROR")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        raise APIException("Formato no soportado. Usa JPG, PNG o WEBP.", 400, "VALIDATION_ERROR")

    # ── Guardar archivo ───────────────────────────────────────────────────────
    upload_dir = os.path.join(os.getcwd(), "uploads", "proofs")
    os.makedirs(upload_dir, exist_ok=True)

    safe_name  = secure_filename(f"{username}_{plan_id}_{int(datetime.now().timestamp())}{ext}")
    image_path = os.path.join(upload_dir, safe_name)
    file.save(image_path)
    logger.info(f"[PaymentProof] Imagen guardada: {image_path}")

    # ── Analizar con Gemini Vision ────────────────────────────────────────────
    from services.payment_analysis_service import PaymentAnalysisService
    analysis = PaymentAnalysisService().analyze(image_path)
    logger.info(f"[PaymentProof] Análisis Gemini para '{username}': {analysis}")

    # ── Registrar suscripción pendiente (si no existe) ────────────────────────
    current_sub = repo.get_user_subscription(username)
    sub_id_for_proof = None

    if not current_sub or current_sub["plan_id"] != plan_id:
        ok, status = repo.subscribe(username, plan_id)
        if ok:
            new_sub = repo.get_user_subscription(username)
            sub_id_for_proof = new_sub["id"] if new_sub else None
    else:
        sub_id_for_proof = current_sub["id"]

    # ── Guardar comprobante en BD ─────────────────────────────────────────────
    proof_id = repo.create_payment_proof(
        username=username,
        plan_id=plan_id,
        image_path=image_path,
        analysis=analysis,
        subscription_id=sub_id_for_proof,
    )

    # ── Notificar al Administrador por WhatsApp ───────────────────────────────
    from core.config.settings import settings
    admin_number = settings.admin_whatsapp_number
    if admin_number:
        from services.channel_adapters import get_unified_channel_service
        channel_service = get_unified_channel_service()
        
        amount = analysis.get("amount", "Desconocido")
        currency = analysis.get("currency", "")
        ref = analysis.get("reference", "Sin ref")
        bank = analysis.get("bank", "Desconocido")
        
        msg_text = (
            f"🔔 *Nuevo Comprobante de Pago*\n\n"
            f"👤 Usuario: {username}\n"
            f"📦 Plan: {plan['name']}\n"
            f"💰 Monto Detectado: {amount} {currency}\n"
            f"🔖 Referencia: {ref} (Banco: {bank})\n\n"
            f"Para *aprobar* este pago, respóndeme:\n"
            f"`SI {proof_id}`\n\n"
            f"Para *rechazarlo*, respóndeme:\n"
            f"`NO {proof_id} [motivo]`"
        )
        
        channel_service.send_outgoing_message(
            channel_name="whatsapp",
            recipient_id=admin_number,
            content=msg_text
        )

    response = {
        "ok":       True,
        "proof_id": proof_id,
        "plan":     plan,
        "analysis": {
            "amount":        analysis.get("amount"),
            "currency":      analysis.get("currency"),
            "reference":     analysis.get("reference"),
            "bank":          analysis.get("bank"),
            "date":          analysis.get("date"),
            "is_valid_proof": analysis.get("is_valid_proof"),
        },
        "message": (
            "✅ Comprobante recibido y analizado. El administrador lo revisará "
            "y activará tu cuenta en breve."
            if analysis.get("is_valid_proof")
            else
            "⚠️ Comprobante recibido, pero Gemini no pudo verificarlo como un "
            "comprobante bancario válido. El administrador lo revisará manualmente."
        ),
    }

    if analysis.get("error"):
        response["analysis_error"] = analysis["error"]

    return jsonify(response), 202


# ─── GET /api/subscriptions/pending-payments  (admin) ────────────────────────

@subscription_bp.route("/pending-payments", methods=["GET"])
def pending_payments():
    """Lista todos los comprobantes de pago (admin)."""
    _require_admin_role()
    repo = _get_repo()
    proofs = repo.get_pending_proofs()
    return jsonify({"ok": True, "proofs": proofs, "total": len(proofs)}), 200


# ─── POST /api/subscriptions/proof/<id>/confirm  (admin) ─────────────────────

@subscription_bp.route("/proof/<int:proof_id>/confirm", methods=["POST"])
def confirm_payment(proof_id: int):
    """
    Admin confirma el pago → activa la suscripción del usuario.

    Body JSON opcional:
        { "note": "Verificado $79 en cuenta bancaria" }
    """
    _require_admin_role()
    admin = get_current_user().get("sub")
    data  = request.get_json(silent=True) or {}
    note  = data.get("note")
    repo  = _get_repo()

    proof = repo.get_proof(proof_id)
    if not proof:
        raise APIException(f"Comprobante #{proof_id} no encontrado", 404, "NOT_FOUND")
    if proof["status"] != "pending":
        raise APIException(
            f"Este comprobante ya fue {proof['status']}", 409, "CONFLICT"
        )

    # Actualizar comprobante
    repo.update_proof_status(proof_id, "confirmed", admin, note)

    # Activar suscripción vinculada
    if proof.get("subscription_id"):
        repo.activate(proof["subscription_id"])
        logger.info(
            f"[PaymentProof] Admin '{admin}' confirmó proof #{proof_id} → "
            f"suscripción #{proof['subscription_id']} activada para '{proof['username']}'"
        )

    return jsonify({
        "ok":      True,
        "message": f"Pago confirmado. Suscripción de '{proof['username']}' al plan '{proof['plan_name']}' activada.",
    }), 200


# ─── POST /api/subscriptions/proof/<id>/reject  (admin) ──────────────────────

@subscription_bp.route("/proof/<int:proof_id>/reject", methods=["POST"])
def reject_payment(proof_id: int):
    """
    Admin rechaza el comprobante de pago.

    Body JSON:
        { "note": "Monto incorrecto, se esperaba $79" }
    """
    _require_admin_role()
    admin = get_current_user().get("sub")
    data  = request.get_json(silent=True) or {}
    note  = data.get("note", "Pago rechazado por el administrador")
    repo  = _get_repo()

    proof = repo.get_proof(proof_id)
    if not proof:
        raise APIException(f"Comprobante #{proof_id} no encontrado", 404, "NOT_FOUND")
    if proof["status"] != "pending":
        raise APIException(
            f"Este comprobante ya fue {proof['status']}", 409, "CONFLICT"
        )

    repo.update_proof_status(proof_id, "rejected", admin, note)
    logger.info(f"[PaymentProof] Admin '{admin}' rechazó proof #{proof_id} de '{proof['username']}'")

    return jsonify({
        "ok":      True,
        "message": f"Comprobante rechazado. Motivo: {note}",
    }), 200


# ── Import datetime needed by upload_payment_proof ────────────────────────────
from datetime import datetime  # noqa: E402
