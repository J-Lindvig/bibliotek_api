from __future__ import annotations

import logging

_LOGGER: logging.Logger = logging.getLogger(__package__)
_LOGGER = logging.getLogger(__name__)

# RAW API CODE BELOW
from bs4 import BeautifulSoup as BS
from datetime import datetime
import json
import requests
import re


DEBUG = True

LOGGED_IN = "logget ind"
MY_PAGES = "MY_PAGES"
LOANS_OVERDUE = "LOANS_OVERDUE"
LOANS = "LOANS"
RESERVATIONS_READY = "RESERVATIONS_READY"
RESERVATIONS = "RESERVATIONS"
#CHECKLIST = "CHECKLIST"	# JS
#SEARCHES = "SEARCHES"		# JS
USER_PROFILE = "USER_PROFILE"
DEBTS = "DEBTS"
LOGOUT = "LOGOUT"
URLS = {
	"FALLBACK": "https://fmbib.dk",
	"LOGIN_PAGE": "/adgangsplatformen/login?destination=ding_frontpage",
	MY_PAGES: "/user/me/view",
	LOANS_OVERDUE: "Overskredne lån",
	LOANS: "Lån",
	RESERVATIONS_READY: "Reserveringer klar til afhentning",
	RESERVATIONS: "Reserveringer i kø",
#	CHECKLIST: "Min liste",				# JS
#	SEARCHES: "Mine gemte søgninger",	# JS
	USER_PROFILE: "Brugerprofil",
	DEBTS: "Betal gebyrer",
	LOGOUT: "Log ud"
	}
TITLE_STRS = {LOGGED_IN: "logget ind", MY_PAGES: "user profile"}

HEADERS = {
	"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
	"Accept-Encoding": "gzip, deflate, br",
	"Accept-Language": "da,en-US;q=0.9,en;q=0.8",
	"Dnt": "1",
	"Upgrade-Insecure-Requests": "1",
	"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
}

class library:
	session = requests.Session()
	session.headers = HEADERS

	baseUrl = None			# The URL to the library
	loggedIn = False
	libraryName = None
	user = None

	def __init__(self, userId: str, pincode: str, url = None, libraryName = None):
		self.user = libraryUser(userId=userId, pincode=pincode)
		if url:
			self.baseUrl = url
		elif libraryName:
			r = self.session.get(URLS["FALLBACK"] + URLS["LOGIN_PAGE"])
			soup = BS(r.text, "html.parser")

			# Fetch the list of libraries, convert to JSON
			libraries = json.loads(soup.find("script", text=re.compile(r'^var libraries = (.)', re.MULTILINE | re.DOTALL)).string.replace("var libraries = ", ""))
			
			# Loop the "Folk" libraries, search for our Library name
			for lib in libraries["folk"]:
				if lib["name"].lower() == libraryName.lower():
					# Extract the baseUrl and return it
					p = re.compile("^.+?[^\/:](?=[?\/]|$)")
					m = p.match(lib["registrationUrl"])
					if m:
						self.baseUrl = m.group()

	def login(self):
		# Test if we are logged in
		r = self.session.get(self.baseUrl)
		if r.status_code == 200:
			self.loggedIn = self._titleInSoup(BS(r.text, "html.parser"), LOGGED_IN)

		if not self.loggedIn:
			# Fetch the loginpage and prepare a soup
			r = self.session.get(self.baseUrl + URLS["LOGIN_PAGE"])
			soup = BS(r.text, "html.parser")

			# Prepare the payload
			payload = {}
			# Find the <form>		
			form = soup.find("form")
			for input in form.find_all("input"):
				# Fill the form with the userInfo
				if input["name"] in self.user.userInfo:
					payload[input["name"]] = self.user.userInfo[input["name"]]
				# or pass default values to payload
				else:
					payload[input["name"]] = input["value"]

			# Send the payload a POST and prepare a new soup
			r = self.session.post(form["action"].replace("/login", r.url), payload)
			soup = BS(r.text, "html.parser")

			# Set loggedIn
			self.loggedIn = self._titleInSoup(soup, LOGGED_IN)
			self.libraryName = soup.title.string.split("|")[0].strip()
		
		return self.loggedIn

	def _fetchPage(self, url = str, payload = None):
		if payload:
			r = self.session.post(url, data = payload)
		else:
			r = self.session.get(url)
		return BS(r.text, "html.parser")

	def _titleInSoup(self, soup, key):
		return TITLE_STRS[key] in soup.title.string.lower()

	def _getDatetime(self, date, format = "%d. %b %Y"):
		d, m, y = date.split(" ")
		m = m[:3]
		match m.lower():
			case "maj":
				m = "may"
			case "okt":
				m = "oct"
		return datetime.strptime(f"{d} {m} {y}", format)

	def fetchUserLinks(self):

		def exctractNumber(a_status):
			return a_status.parent.find_all("span")[-1].string

		# Fetch "My view"
		soup = self._fetchPage(self.baseUrl + URLS[MY_PAGES])
		# Find all <a> containing "user" in the href
		for userPage in soup.select_one("ul[class=main-menu-third-level]").find_all("a"):
			# Only work on URLs not allready in our dict
			if not userPage["href"] in URLS.values():
				# Search for value, return the key and update the URLS
				for key, value in URLS.items():
					if value in userPage.text:
						URLS[key] = userPage["href"]

		# Fetch usefull user states - OBSOLETE WHEN FETCHING DETAILS
		for a_status in soup.select_one("ul[class='list-links specials']").find_all("a"):
			if URLS[DEBTS] in a_status["href"]:
				self.user.debts = exctractNumber(a_status)
		
	def fetchUserInfo(self):
		r = self.session.get(self.baseUrl + URLS[USER_PROFILE])
		soup = BS(r.text, "html.parser")
		for fields in soup.select_one("div[class=content]").select("div[class*=field-name]"):
			# Crappy HTML page....
			# Find the fieldName tag
			fieldName = fields.select_one("div[class=field-label]")
			# Get the parent of the fieldName tag and extract the value from the sub div
			fieldLine = fieldName.parent.select_one("div[class=field-items]").div
			# Remove <br>
			for e in fieldLine.findAll('br'):
				e.extract()
			# Extract the fieldName from the fieldName tag
			fieldName = fieldName.string.lower()

			match fieldName:
				case "navn":
					self.user.name = fieldLine.string
				case "adresse":
					self.user.address = fieldLine.contents

		# Find the <form>, extract info
		form = soup.select_one(f"form[action='{URLS[USER_PROFILE]}']")
		self.user.phone = form.select_one("input[name*='phone]']")["value"]
		self.user.phoneNotify = int(form.select_one("input[name*='phone_notification']")["value"]) == 1
		self.user.mail = form.select_one("input[name*='mail]']")["value"]
		self.user.mailNotify = int(form.select_one("input[name*='mail_notification']")["value"]) == 1
		for library in form.select_one("select[name*='preferred_branch']").find_all("option"):
			if "selected" in library.attrs:
				self.user.pickupLibrary = library.string
				break

	def fetchLoans(self):
		r = self.session.get(self.baseUrl + URLS[LOANS])
		soup = BS(r.text, "html.parser")

		materials = soup.select("div[class*='material-item']")
		for material in materials:
			loan = libraryLoan()

			# Renewable
			loan.renewAble = not "disabled" in material.input.attrs
			loan.renewid = material.input["value"]

			# URL and image
			loan.url = self.baseUrl + material.a["href"]
			loan.coverUrl = material.img["src"] if material.img else ""

			# Type, title and creator
			loan.aType = material.select_one("div[class=item-material-type]").string
			loan.title = material.h3.string
			loan.creators = material.select_one("div[class=item-creators]").string if material.select_one("div[class=item-creators]") else ""

			# Dates and ID
			for li in material.find_all("li"):
				value = li.select_one("div[class=item-information-data]").string
				match li["class"][-1]:
					case "loan-date":
						d, m, y = value.split(" ")
						loan.loanDate = self._getDatetime(value)
					case "expire-date":
						d, m, y = value.split(" ")
						loan.expireDate = self._getDatetime(value)
					case "material-number":
						loan.id = value
			
			# Add the loan to the stack
			self.user.loans.append(loan)

		self.user.loans.sort(key=lambda x: (x.expireDate, x.title))
		if self.user.loans:
			self.user.nextExpireDate = self.user.loans[0].expireDate

		print(self.user.nextExpireDate)

	def fetchReservations(self):
		r = self.session.get(self.baseUrl + URLS[RESERVATIONS])
		soup = BS(r.text, "html.parser")

		materials = soup.select("div[class*='material-item']")
		for material in materials:
			reservation = libraryReservation()

			reservation.id = material.input["value"]
			reservation.url = self.baseUrl + material.a["href"] if material.a else ""
			reservation.coverUrl = material.img["src"] if material.img else ""
			reservation.aType = material.select_one("div[class=item-material-type]").string if material.select_one("div[class=item-material-type]") else ""
			reservation.title = material.h3.string
			reservation.creators = material.select_one("div[class=item-creators]").string if material.select_one("div[class=item-creators]") else ""

			for li in material.find_all("li"):
				value = li.select_one("div[class=item-information-data]").string
				match li["class"][-1]:
					case "expire-date":
						reservation.expireDate = self._getDatetime(value)
					case "created-date":
						reservation.createdDate = self._getDatetime(value)
					case "queue-number":
						reservation.queueNumber = value
					case "pickup-branch":
						reservation.pickupLibrary = value

			# Add the reservation to the stack
			self.user.reservations.append(reservation)

#		with open(f"response.html", mode="w", encoding="utf-8") as resp_file:
#			resp_file.write(r.text)

class libraryUser:
	userInfo = None
	name, address = None, None
	phone, phoneNotify, mail, mailNotify = None, None, None, None
	reservations, loans, debts = [], [], None
	nextExpireDate = None
	pickupLibrary = None

	def __init__(self, userId: str, pincode: str):
		self.userInfo = {"userId": userId, "pincode": pincode}

class libraryMaterial:
	id = None
	aType, title, creators = None, None, None
	url, coverUrl = None, None

class libraryLoan(libraryMaterial):
	loanDate, expireDate = None, None
	renewid, renewAble = None, None

class libraryReservation(libraryMaterial):
	createdDate, expireDate, queueNumber = None, None, None
	pickupLibrary = None