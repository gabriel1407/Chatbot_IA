import requests
import json

OPENAI_API_KEY = 'sk-proj-eamaqYzfj6oNk4QY15dmT3BlbkFJSfBH9zf6TSwiqEijyVm0'

headers = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
}

# Subir el archivo de entrenamiento con el campo 'purpose'
files = {
    'file': open('training_data.jsonl', 'rb')
}
data = {
    'purpose': 'fine-tune'
}

response = requests.post('https://api.openai.com/v1/files', headers=headers, files=files, data=data)
print("Response from file upload:", response.text)  # Imprime la respuesta completa

try:
    file_id = response.json()['id']
    print(f"File ID: {file_id}")
except KeyError:
    print("Error: 'id' not found in the response. Full response:")
    print(response.json())
    exit()

# Crear el fine-tune
data = {
    "training_file": file_id,
    "model": "davinci"  # Usa el modelo adecuado, "davinci" en este caso
}

response = requests.post('https://api.openai.com/v1/fine-tunes', headers=headers, json=data)
print("Response from fine-tune creation:", response.text)  # Imprime la respuesta completa

try:
    fine_tune_id = response.json()['id']
    print(f"Fine-tune ID: {fine_tune_id}")
except KeyError:
    print("Error: 'id' not found in the response. Full response:")
    print(response.json())
    exit()

# Monitorear el progreso
response = requests.get(f'https://api.openai.com/v1/fine-tunes/{fine_tune_id}', headers=headers)
print("Response from fine-tune status:", response.text)  # Imprime la respuesta completa

# Uso del modelo fino ajustado
data = {
    "model": fine_tune_id,
    "prompt": "¿Cómo estás?",
    "max_tokens": 50
}

response = requests.post('https://api.openai.com/v1/completions', headers=headers, json=data)
print("Response from completion request:", response.text)  # Imprime la respuesta completa

try:
    print(response.json()['choices'][0]['text'].strip())
except KeyError:
    print("Error: 'choices' not found in the response. Full response:")
    print(response.json())
