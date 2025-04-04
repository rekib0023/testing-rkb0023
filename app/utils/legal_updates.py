import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from datetime import datetime
import json


class LegalUpdates:
    def __init__(self):
        self.base_urls = {
            "india_code": "https://www.indiacode.nic.in/",
            "prsindia": "https://prsindia.org/billtrack/",
            "legislative_gov": "https://legislative.gov.in/",
        }

    def get_recent_bills(self) -> List[Dict[str, Any]]:
        """Fetch recent bills from PRS India."""
        try:
            response = requests.get(self.base_urls["prsindia"])
            soup = BeautifulSoup(response.text, "html.parser")

            bills = []
            bill_elements = soup.select(
                ".bill-item"
            )  # Update selector based on actual HTML

            for element in bill_elements:
                bill = {
                    "title": element.select_one(".bill-title").text.strip(),
                    "status": element.select_one(".bill-status").text.strip(),
                    "date": element.select_one(".bill-date").text.strip(),
                    "url": element.select_one("a")["href"],
                }
                bills.append(bill)

            return bills
        except Exception as e:
            print(f"Error fetching recent bills: {str(e)}")
            return []

    def get_constitution_amendments(self) -> List[Dict[str, Any]]:
        """Fetch recent constitution amendments."""
        try:
            response = requests.get(
                f"{self.base_urls['legislative_gov']}/constitution-amendments"
            )
            soup = BeautifulSoup(response.text, "html.parser")

            amendments = []
            amendment_elements = soup.select(
                ".amendment-item"
            )  # Update selector based on actual HTML

            for element in amendment_elements:
                amendment = {
                    "number": element.select_one(".amendment-number").text.strip(),
                    "description": element.select_one(".amendment-desc").text.strip(),
                    "date": element.select_one(".amendment-date").text.strip(),
                    "url": element.select_one("a")["href"],
                }
                amendments.append(amendment)

            return amendments
        except Exception as e:
            print(f"Error fetching constitution amendments: {str(e)}")
            return []

    def get_section_updates(self, section_number: str) -> List[Dict[str, Any]]:
        """Fetch updates for a specific section of law."""
        try:
            response = requests.get(
                f"{self.base_urls['india_code']}/section/{section_number}"
            )
            soup = BeautifulSoup(response.text, "html.parser")

            updates = []
            update_elements = soup.select(
                ".section-update"
            )  # Update selector based on actual HTML

            for element in update_elements:
                update = {
                    "date": element.select_one(".update-date").text.strip(),
                    "description": element.select_one(".update-desc").text.strip(),
                    "reference": element.select_one(".update-ref").text.strip(),
                }
                updates.append(update)

            return updates
        except Exception as e:
            print(f"Error fetching section updates: {str(e)}")
            return []

    def save_updates_to_file(
        self, updates: List[Dict[str, Any]], filename: str
    ) -> None:
        """Save updates to a JSON file."""
        try:
            with open(filename, "w") as f:
                json.dump(updates, f, indent=2)
        except Exception as e:
            print(f"Error saving updates to file: {str(e)}")

    def load_updates_from_file(self, filename: str) -> List[Dict[str, Any]]:
        """Load updates from a JSON file."""
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading updates from file: {str(e)}")
            return []
