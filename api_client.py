
import requests

MY_API = "https://jasminerose-2.onrender.com"

# Replace this with your classmate's real API URL
CLASSMATE_API = ""

TIMEOUT = 60


def fetch_api(url):
    try:
        print("\nConnecting to Student API...")

        response = requests.get(url, timeout=TIMEOUT)

        print("Status Code:", response.status_code)

        response.raise_for_status()

        return response.json()

    except requests.exceptions.Timeout:
        print("Connection timed out.")
        print("The Render service may be starting.")

    except requests.exceptions.RequestException as error:
        print("Connection error:", error)

    except ValueError:
        print("The server did not return valid JSON.")

    return None


def view_about():
    data = fetch_api(MY_API + "/about")

    if not isinstance(data, dict):
        return

    print("\n" + "=" * 35)
    print("           ABOUT ME")
    print("=" * 35)

    print("Name     :", data.get("name", "Not provided"))
    print("Program  :", data.get("program", "Not provided"))
    print("Year     :", data.get("year", "Not provided"))
    print("Section  :", data.get("section", "Not provided"))
    print("Interest :", data.get("interest", "Not provided"))

    print("=" * 35)
    print("API accessed successfully!")


def display_records(url, title):
    data = fetch_api(url)

    if data is None:
        return

    if isinstance(data, dict):
        students = data.get("students", [])
    elif isinstance(data, list):
        students = data
    else:
        print("Unexpected API response.")
        return

    print("\n" + "=" * 45)
    print(title.center(45))
    print("=" * 45)

    for student in students:
        print("Student ID :", student.get("student_id"))
        print("Name       :", student.get("name"))
        print("Program    :", student.get("program"))
        print("Year       :", student.get("year"))
        print("Section    :", student.get("section"))
        print("-" * 45)

    print("Total Records:", len(students))


def main():
    while True:
        print("\n" + "=" * 45)
        print("        LABORATORY ACTIVITY 8")
        print("       FLASK REST API CLIENT")
        print("=" * 45)

        print("1. View About Me")
        print("2. View My Records")
        print("3. View Classmate's Records")
        print("4. Exit")

        choice = input("\nEnter choice: ").strip()

        if choice == "1":
            view_about()

        elif choice == "2":
            display_records(
                MY_API + "/api/students",
                "MY STUDENT RECORDS"
            )

        elif choice == "3":
            if CLASSMATE_API:
                display_records(
                    CLASSMATE_API,
                    "CLASSMATE'S RECORDS"
                )
            else:
                print("Configure CLASSMATE_API first.")

        elif choice == "4":
            print("Thank you for using the API!")
            break

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
