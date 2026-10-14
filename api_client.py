import requests

url = "https://jasminerose-2.onrender.com/student"

try:
    response = requests.get(url, timeout=60)

    print("Status Code:", response.status_code)
    print("Response:", response.text)

    if response.status_code == 200:
        try:
            data = response.json()

            print("\nSTUDENT INFORMATION")
            print("-------------------")
            print("Student ID:", data.get("student_id"))
            print("Name:", data.get("name"))
            print("Program:", data.get("program"))
            print("Year:", data.get("year"))
            print("Section:", data.get("section"))

        except ValueError:
            print("Error: The API response is not valid JSON.")

    else:
        print("Request failed. Check your Render API.")

except requests.RequestException as error:
    print("Connection error:", error)