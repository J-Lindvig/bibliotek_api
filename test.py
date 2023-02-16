from library_api import library

userId = "12345678"   # CPR nummer uden "-"
pincode = "1234"        # Pinkode til bibliotekssiden

#brobybib = library(userId=userId, pincode=pincode, url="https://fmbib.dk/")
brobybib = library(userId=userId, pincode=pincode, libraryName = "Faaborg-Midtfyn")

brobybib.login()
brobybib.fetchUserLinks()
brobybib.fetchUserInfo()
brobybib.fetchLoans()
brobybib.fetchReservations()


print(f"{brobybib.libraryName}")
print(f"----------------------------------------")
print(f"Navn:          {brobybib.user.name}")
print(f"Telefon:       {brobybib.user.phone} [{'X' if brobybib.user.phoneNotify else ' '}]")
print(f"Mail:          {brobybib.user.mail} [{'X' if brobybib.user.mailNotify else ' '}]")
print(f"Adresse:       {brobybib.user.address}")
print()
print(f"Bibliotek:     {brobybib.user.pickupLibrary}")
print()
print(f"Næste afleveringsdato: {brobybib.user.nextExpireDate}")
print()
print(f"Lån:           {len(brobybib.user.loans)}")
for loan in brobybib.user.loans:
    print(f"   {loan.title} ({loan.coverUrl})")
print()
print(f"Reservationer: {len(brobybib.user.reservations)}")
for reservation in brobybib.user.reservations:
    print(f"   {reservation.title}")
print()
print(f"Gebyrer:       {brobybib.user.debts}")
