import requests

url = "https://baby-apostol.onrender.com/student"

try:
    response = requests.get(url, timeout=60)

    print("Status Code:", response.status_code)

    if response.status_code == 200:
        try:
            data = response.json()

            print("\nCLASSMATE API DATA")
            print("------------------")
            print("Student ID:", data.get("student_id", "Not provided"))
            print("Name:", data.get("name", "Not provided"))
            print("Program:", data.get("program", "Not provided"))
            print("Year:", data.get("year", "Not provided"))
            print("Section:", data.get("section", "Not provided"))

            print("\nAPI accessed successfully!")

        except ValueError:
            print("Error: The endpoint did not return valid JSON.")
            print(response.text)

    else:
        print("Request failed.")
        print(response.text)

except requests.RequestException as error:
    print("Connection error:", error)