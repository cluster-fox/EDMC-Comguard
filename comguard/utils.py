import functools
import re
from os import listdir
from os.path import join
from pathlib import Path

import semantic_version

from comguard.debug import Debug
from config import appversion


def human_format(num: int) -> str:
    """
    Format a number into a shortened human-readable string, using abbreviations for larger values, e.g. 1300 -> 1.3K
    """
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])


def tick_format(ticktime):
    """
    Make the Tick human readable
    """ 
    datetime1 = ticktime.split('T')
    months = {"01":"Jan", "02":"Feb", "03":"March", "04":"April", "05":"May", "06":"June", "07":"July", "08":"Aug", "09":"Sep", "10":"Oct", "11":"Nov", "12":"Dec"}
    x = datetime1[0]
    z = datetime1[1]
    y = x.split('-')
    date1 = y[2] + " " + months[y[1]]
    time1 = z[0:5]
    datetimetick = time1 + ' UTC ' + date1
    return (datetimetick)
