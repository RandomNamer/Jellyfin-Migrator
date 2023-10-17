import pathlib
import sqlite3
import json
import hashlib
import binascii
import xml.etree.ElementTree as ET
from pathlib import Path
from shutil import copy
from time import time
from jellyfin_id_scanner import *
import datetime
from string import ascii_letters
import os

'''
Here's the simpler and trouble free solution if you just want to move your media files to another place and not migrating your Jellyfin installation.
This happens, especially for Windows users who want to move bulky media files to a new drive, 
or their NASs (For example, newer Synology models dropped support for hardware accelerated transcoding, users might still want to deploy Jellyfin to another machine while storing files on DiskStation). 

What this script do is basically replacing all file paths in Jellyfin's monolithic DB for media libraries, all other files are not touched.
'''

source_root = Path("E:/JellyfinSvrData_bk")
target_root = Path("E:/JellyfinSvrData_new")

path_replacements = {
    # Self-explanatory, I guess. "\\" if migrating *to* Windows, "/" else.
    "target_path_slash": "\\",
    # Paths to your libraries
    "E:/Media Libraries/Anime": "X:/Anime",
    "E:/Media Libraries/Movies": "X:/Movies",
    "E:/Media Libraries/Shows": "X:/Shows",
    "E:/Downloads.old": "X:/Old/Downloads.old",
    "D:/Downloads": "Y:/Downloads"
}

library_db_config = {
        "source": source_root / "data/library.db",
        "target": "auto",                      # Usually you want to leave this on auto. If you want to work on the source file, set it to the same path (YOU SHOULDN'T!).
        "replacements": path_replacements,     # Usually same for all but you could specify a specific one per db.
        "tables": {
            "TypedBaseItems": {        # Name of the table within the SQLite database file
                "path_columns": [      # All column names that can contain paths.
                    "Path",
                ],
                "jf_image_columns": [  # All column names that can jellyfins "image paths mixed with image properties" strings.
                    "Images",
                ],
                "json_columns": [      # All column names that can contain json data with paths.
                    "data",
                ],
            },
            "mediastreams": {
                "path_columns": [
                    "Path",
                ],
            },
            "Chapters2": {
                "jf_image_columns": [
                    "ImagePath",
                ],
            },
        },
    }
main_db_config = {
        "source": source_root / "data/jellyfin.db",
        "target": "auto",
        "replacements": path_replacements,
        "tables": {
            "ImageInfos": {
                "path_columns": [
                    "Path",
                ],
            },
        },
}

def update_file_path(db_config, new_file_name):
    copy(db_config["source"], target_root / new_file_name)
    con = sqlite3.connect(target_root / new_file_name)
    cur = con.cursor()
    for (table, col_desc) in db_config['tables'].items():
        target_columns = [] 
        if col_desc.__contains__('path_columns'):
            target_columns.extend(col_desc['path_columns'])
        if col_desc.__contains__('jf_image_columns'):
            target_columns.extend(col_desc['jf_image_columns'])
        print(f"path-like cols for {table}: {target_columns}")
        query = "SELECT `rowid` "
        for col in target_columns:
            query += f", `{col}` "
        query += f" FROM {table}"
        rows = [r for r in cur.execute(query)]
        print(f"total {len(rows)} entries for {table}")
        delimiter = path_replacements['target_path_slash']
        for row in rows:
            rowid = row[0]
            modified_columns = list(row)[1:]
            update_query = f"UPDATE `{table}` SET " + ','.join([f"`{c}` = ?" for c in target_columns]) + f" WHERE `rowid` = {rowid}"
            for i, col in enumerate(modified_columns):
                modified_columns[i] = find_replacement(col, delimiter)
            cur.execute(update_query, modified_columns)
        con.commit()
        print("done")
            

                



def find_replacement(original, delimiter):
    if not original: return original
    else:
        old_path = Path(original)
        new_path = Path()
        for k,v in path_replacements.items():
            if old_path.is_relative_to(k):
                new_path = v / old_path.relative_to(k)
                return new_path.as_posix().replace("/", delimiter)
        return original

                
                    
if __name__ == "__main__":
    update_file_path(library_db_config, 'library.db')
    update_file_path(main_db_config, 'jellyfin.db')