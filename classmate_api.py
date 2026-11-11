import requests

url = "https://johnmarkalarba.onrender.com/api/students"

try:
    response = requests.get(url, timeout=60)

    print("Status Code:", response.status_code)

    if response.status_code == 200:
        try:
            data = response.json()

            print("\nCLASSMATE API DATA")
            print("------------------")

            # Handle a list of students
            if isinstance(data, list):
                if not data:
                    print("No student records found.")
                else:
                    for index, student in enumerate(data, start=1):
                        print(f"\nStudent {index}")
                        print("Student ID:", student.get("student_id", "Not provided"))
                        print("Name:", student.get("name", "Not provided"))
                        print("Program:", student.get("program", "Not provided"))
                        print("Year:", student.get("year", "Not provided"))
                        print("Section:", student.get("section", "Not provided"))

            # Handle a single student or a dictionary containing students
            elif isinstance(data, dict):
                students = data.get("students")

                if isinstance(students, list):
                    for index, student in enumerate(students, start=1):
                        print(f"\nStudent {index}")
                        print("Student ID:", student.get("student_id", "Not provided"))
                        print("Name:", student.get("name", "Not provided"))
                        print("Program:", student.get("program", "Not provided"))
                        print("Year:", student.get("year", "Not provided"))
                        print("Section:", student.get("section", "Not provided"))
                else:
                    print("Student ID:", data.get("student_id", "Not provided"))
                    print("Name:", data.get("name", "Not provided"))
                    print("Program:", data.get("program", "Not provided"))
                    print("Year:", data.get("year", "Not provided"))
                    print("Section:", data.get("section", "Not provided"))

            else:
                print("Unexpected API response format:")
                print(data)

            print("\nAPI accessed successfully!")

        except ValueError:
            print("Error: The endpoint did not return valid JSON.")
            print("Response:", response.text[:1000])

    else:
        print("Request failed.")
        print("Response:", response.text[:1000])

except requests.RequestException as error:
    print("Connection error:", error)