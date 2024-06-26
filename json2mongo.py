import urllib.parse
import argparse
import json

import pymongo
from tqdm import tqdm


def init_argparse():
    args = argparse.ArgumentParser(description="Insert JSON data into MongoDB", formatter_class=argparse.RawTextHelpFormatter)
    args.add_argument("-a", "--address", default="127.0.0.1", help="MongoDB host address, default 127.0.0.1")
    args.add_argument("-p", "--port", default=27017, help="MongoDB port, default 27017")

    args.add_argument("-u", "--user", help="MongoDB username")
    args.add_argument("-P", "--password", help="MongoDB password")

    args.add_argument("-k", "--key", help="Specificing key to check for upsert operation\nIf not specified, all records will be inserted")
    args.add_argument("-d", "--database", help="Specificing database name", required=True)
    args.add_argument("-c", "--collection", help="Specificing collection name", required=True)
    args.add_argument("-f", "--file", help="JSON file path", required=True)

    return args.parse_args()


def construct_mongo_uri(address, port, user: str = None, password: str = None):
    if user and password:
        encoded_user = urllib.parse.quote_plus(user)
        encoded_password = urllib.parse.quote_plus(password)
        return f"mongodb://{encoded_user}:{encoded_password}@{address}:{port}"
    return f"mongodb://{address}:{port}"


def main(mongo_str: str, file_path: str, database: str, collection: str, key: str):
    client = None
    try:
        client = pymongo.MongoClient(mongo_str)
    except Exception as e:
        print(e)

    data_list = read_file_content(file_path)
    print(f"Finish Loading, total {len(data_list)} records loaded")
    db = client[database]
    table = db[collection]

    try:
        if key and check_collection_exist(db, collection):
            for data in tqdm(data_list):
                table.replace_one({key: data[key]}, data, upsert=True)
        else:
            # use insert_many for the first inseration
            table.insert_many(data_list)
    except pymongo.errors.ServerSelectionTimeoutError as e:
        print(f"Please check your MongoDB connection\n{e}")
    except pymongo.errors.OperationFailure as e:
        print(f"Connection required authentication\n{e}")

    if client:
        client.close()


def check_collection_exist(db: pymongo.database.Database, collection: str) -> bool:
    # check if collection already exist in database
    return collection in db.list_collection_names()


def read_file_content(file_path: str) -> list[dict]:
    print(f"Loading JSON file: {file_path}")
    try:
        with open(file_path, "r") as f:
            try:
                return json.load(f)  # when input file is: [{}, {}, {}]
            except json.decoder.JSONDecodeError:
                # when input file is: {}\n{}\n{}\n...\n{}
                f.seek(0)
                return [json.loads(line.strip()) for line in f]
    except FileNotFoundError:
        print(f"File not found: {file_path}")


if __name__ == "__main__":
    args = init_argparse()
    mongo_str = construct_mongo_uri(args.address, args.port, args.user, args.password)
    main(mongo_str, args.file, args.database, args.collection, args.key)

