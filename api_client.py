import requests

url = "https://jasminerose-2.onrender.com/about"

try:
    response = requests.get(url, timeout=60)

    if response.status_code == 200:
        data = response.json()

        print("ABOUT ME")
        print("------------------")
        print("Name:", data.get("name", "Not provided"))
        print("Program:", data.get("program", "Not provided"))
        print("Year:", data.get("year", "Not provided"))
        print("Section:", data.get("section", "Not provided"))
        print("Interest:", data.get("interest", "Not provided"))

        print("\nAPI accessed successfully!")

    else:
        print("Request failed.")
        print("Status Code:", response.status_code)
        print(response.text)

except requests.RequestException as error:
    print("Connection error:", error)