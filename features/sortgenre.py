import json
from array import array as arr
from collections import defaultdict
from main import FILES


json_path = FILES['streams']


"""   
#backend part:

need to get access to valid channels json
get group_title from json
store group_title into their respective genre maybe use json
implement a function to show this on webpage 

#frontend part:

create sort by buttons for genre
"""

def GetGroupTitle(json_path) -> str:
    with open(json_path, 'r') as file:
        data = json.load(file)
        return data['group_title']
    print("printed group titles")
    

    