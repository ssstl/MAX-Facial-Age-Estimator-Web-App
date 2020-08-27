import pymongo

def bad(request):
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["db"]
    collection = db["collection"]
    username = request.GET["username"]
    password = request.GET["password"]
    results = collection.find(
        {"$where": "this.owner == \"" + username + "\" && this.password == \"" + password + "\""});
