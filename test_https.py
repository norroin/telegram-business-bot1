import requests

r = requests.get("https://api.telegram.org")

print(r.status_code)
print(r.text[:100])