import requests

url = "https://exp.host/--/api/v2/push/send"

data = {
    "to": "ExponentPushToken[faCMYSCNxn3ZnqmPv71vTu]",
    "title": "Teste EloMind",
    "body": "Funcionou 🚀"
}

response = requests.post(url, json=data)

print("STATUS:", response.status_code)
print("RESPOSTA:", response.json())