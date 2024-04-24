# -*- coding: utf-8 -*-
"""
A script for gathering alias associations from an IOC
@author: aberges
"""
###############################################################################
# %% Imports
###############################################################################

import sys
import re
import os.path
import argparse
import json
import copy
import glob as gb
from colorama import Fore, Style
from prettytable import PrettyTable

###############################################################################
# %% Functions
###############################################################################


def simple_prompt(prompt: str, default: str = 'N') -> bool:
    """
    Simple yes/no prompt which defaults to 'N' = False, but can be changed.

    Returns
    -------
    bool
        Prompted yes/no response

    """
    while True:
        p = input(prompt).strip().lower()
        if p in ['']:
            p = default.lower()
        if p[0] == 'y':
            result = True
            break
        if p.lower()[0] == 'n':
            result = False
            break
        print('Invalid Entry. Please choose again.')
    return result


def request_file_dest(prompt: str,
                      default: str = os.getcwd(),) -> str:
    """
    Requests the user for a destination to save a file.
    Tests if the resultant path exists and makes the directory if necessary.

    Parameters
    ----------
    prompt: str
        Prompt to show the user
    default: str
        File destination to default to.
        Default is '{current_dir}'
    Returns
    -------
    str
        Path to file destination.
    """
    while True:
        p = input(prompt+f'(default = {default}): ')
        # Check for default
        if p in ['']:
            result = default
        else:
            result = p
        confirm = simple_prompt('Is '
                                + Fore.LIGHTYELLOW_EX + f'{result} '
                                + Style.RESET_ALL
                                + 'correct? (y/N): ')
        if confirm is True:
            break
    return result


def flatten_list(input_list: list[list]) -> list[str]:
    """
    Flatten a 2D lists and find its unique values.
    Note: loses order due to set() call.

    Parameters
    ----------
    input_list: list[list]
        The 2D list to flatten.

    Returns
    -------
    list
        The list of unique elements from the 2D input_list
    """
    _result = [e for lst in input_list for e in lst]
    return list(set(_result))


def search_file(*, file: str, patt: str = None, prefix: str = '',
                color_wrap: Fore = None) -> list[str]:
    """
    Searches file for regex match and appends result to list

    Parameters
    ----------
    file: str
        The file to read and search. Encoding must be utf-8
    output: list, optional
        A list to appead your results to. The default is None.
    patt: str, optional
        The regex pattern to search for. The default is None.
    prefix: str, optional
        A str prefix to add to each line. The default is ''.
    color_wrap: Fore, optional
        Color wrapping using Colorama.Fore. The default is None.

    Returns
    -------
    list[str]
        A list of the search results with the prefix prepended.
    """
    output = []
    color = ''
    reset = ''
    if color_wrap is not None:
        color = color_wrap
        reset = Style.RESET_ALL
    if os.path.isfile(file) is False:
        print(f'{file} does not exist')
        return ''
    with open(file, 'r', encoding='utf-8') as _f:
        for line in _f.readlines():
            if re.search(patt, line):
                output.append(re.sub(patt, color + r'\g<0>' + reset, line))
        return prefix + prefix.join(output)


def clean_ansi(text: str = None) -> str:
    """
    Removes ANSI escape sequences from a str, including fg/bg formatting.
    """
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def fix_json(raw_data: str) -> list[str]:
    """
    Fixes JSON format of find_ioc/grep_ioc output.

    Parameters
    ----------
    raw_data: str
        Str output generated by find_ioc/grep_ioc, which is pseudo-JSON.
    Returns
    -------
    list[str]
        The list of str ready for JSON loading 
    """
    # clean empty rows and white space
    _temp = raw_data.replace(' ', '').strip()
    # capture and fix the keys not properly formatted to str
    _temp = re.sub(r"(?<!'|\w)\w+(?!')(?=:\s?)", r"'\g<0>'", raw_data)
    # capture boolean tokens and fix them for json format
    _temp = re.sub("True", "true", _temp)
    _temp = re.sub("False", "false", _temp)
    # then capture and fix digits not formatted to str
    _temp = re.sub(r"(?<=:)\d+", r"'\g<0>'", _temp)
    # then properly convert to list of json obj
    result = (_temp
              .replace('\'', '\"')
              .replace('},', '}')
              .replace(' {', '{')
              .strip()
              .split('\n'))
    return result


def find_ioc(hutch: str = None, patt: str = None) -> list[dict]:
    """
    A pythonic grep_ioc for gathering IOC details from the cfg file

    Parameters
    ----------
    hutch: str, optional
        3 letter lowercase hutch code. May also include 'all'.
        The default is None.
    patt: str, optional
        Regex pattern to search for. The default is None.

    Raises
    ------
    ValueError
        Hutch code is invalid or regex pattern is missing.

    Returns
    -------
    list[dict]
        List of dictionaries generated by the JSON loading

    """
    hutch_list = ['xpp', 'xcs', 'cxi', 'mfx', 'mec', 'tmo', 'rix', 'xrt',
                  'aux', 'det', 'fee', 'hpl', 'icl', 'las', 'lfe', 'kfe',
                  'tst', 'txi', 'thz', 'all']
    # check hutches
    if (hutch is None) | (hutch not in tuple(hutch_list)):
        print('Invalid entry. Please choose a valid hutch:\n'
              + ','.join(hutch_list))
        raise ValueError
    # create file paths
    if hutch in tuple(hutch_list):
        if hutch == 'all':
            path = gb.glob('/cds/group/pcds/pyps/config/*/iocmanager.cfg')
        else:
            path = [f'/cds/group/pcds/pyps/config/{hutch}/iocmanager.cfg']
    # check patt and generate the regex pattern
    if patt is None:
        print('No regex pattern supplied')
        raise ValueError
    patt = r'{.*' + patt + r'.*}'
    # initialize output list
    result = []
    # iterate and capture results.
    for _file in path:
        prefix = ''
        if len(path) != 1:
            prefix = _file+':'
        output = search_file(file=_file, patt=patt, prefix=prefix)
        if output != prefix:
            result.append(output)
    # reconstruct the list of str
    _temp = ''.join(result)
    if len(_temp) == 0:
        print(f'{Fore.RED}No results found for {Style.RESET_ALL}{patt}'
              + f'{Fore.RED} in{Style.RESET_ALL}'
              + f'{hutch}')
        return None
    # capture the hutch from the cfg path if hutch = all
    if hutch == 'all':
        hutch_cfgs = re.findall(r'/.*cfg\:', _temp)
        hutch_cfgs = [''.join(re.findall(r'(?<=/)\w+(?=/ioc)', s))
                      for s in hutch_cfgs]
    # strip the file information
    _temp = re.sub(r'.*cfg\:', '', _temp)
    # now convert back to json and load
    output = [json.loads(s) for s in fix_json(_temp)]
    # and add the hutches back into the dicts if searching across all cfgs
    if hutch == 'all':
        for _i, _d in enumerate(output):
            _d['hutch'] = hutch_cfgs[_i]
    return output


def fix_dir(dir_path: str) -> str:
    """
    Simple function for repairing the child release IOC path based on
    the ioc_cfg output. Returns the proper dir for the child IOC.cfg file.

    Parameters
    ----------
    dir_path: str
        The path to the child IOC's directory as a str.

    Returns
    -------
    str
        The typo-corrected path as a str.

    """

    # catches the short form path
    if dir_path.startswith('ioc/'):
        output_dir = '/cds/group/pcds/epics/'+dir_path
    # for the rare, old child IOCs that only exist in their parent's release
    elif 'common' in dir_path:
        output_dir = dir_path + '/children'
    # Otherwise fine!
    else:
        output_dir = dir_path
    # Make sure the end of the path is a folder!
    if output_dir[-1] != '/':
        output_dir += '/'
    return output_dir


def find_parent_ioc(file: str, path: str) -> str:
    """
    Searches the child IOC for the parent's release pointer
    Returns the parent's IOC as a str.

    Parameters
    ----------
    file : str, optional
        DESCRIPTION. The default is None.
    path : str, optional
        DESCRIPTION. The default is None.

    Returns
    -------
    str
        Path to the parent IOC's release.

    """
    file_dir = fix_dir(path)
    if os.path.exists(f'{file_dir}{file}.cfg') is False:
        return 'Invalid. Child does not exist.'
    parent_ioc_release = search_file(file=f'{file_dir}{file}.cfg',
                                     patt='^RELEASE').strip()
    return parent_ioc_release.rsplit('=', maxsplit=1)[-1]


def build_table(input_data: list[dict], columns: list[str] = None,
                **kwargs) -> PrettyTable:
    """
    Build a prettytable from a list of dicts/JSON.
    input_data must be a list(dict)
    Parameters
    ----------
    input_data : list[dict]
        The data to generate a PrettyTable from.
    columns : list, optional
        Columns for the PrettyTable headers. The default is None.
    **kwargs:
        kwargs to pass tohe PrettyTable() for extra customization.

    Returns
    -------
    PrettyTable
        PrettyTable object ready for terminal printing.

    """

    if columns is None:
        col_list = []
    # First get all unique key values from the dict
        for _d in input_data:
            col_list.extend(list(_d.keys()))
        cols = sorted(list(set(col_list)))
    else:
        cols = columns
    # initialize the table
    _tbl = PrettyTable()
    # add the headers
    for c in cols:
        _tbl.add_column(c, [], **kwargs)
    # add the data, strip ANSI color from color headers if any
    for _d in input_data:
        _tbl.add_row([_d.get(clean_ansi(c), '') for c in cols])
    return _tbl


def acquire_aliases(dir_path: str, ioc: str) -> list[dict]:
    """
    Scans the st.cmd of the child IOC for the main PV aliases.
    Returns a list of dicts for the associations. This is the
    top level PV name.
    E.g. LM1K2:MCS2:01:m1 <--> LM2K2:INJ_MP1_MR1

    Parameters
    ----------
    dir_path : str
        Path to the child IOC's release.
    ioc : str
        Child IOC's cfg file name.

    Returns
    -------
    list[dict]
        List of dicts for record <--> alias associations.

    """
    _d = fix_dir(dir_path)
    _f = f'{_d}build/iocBoot/{ioc}/st.cmd'
    if os.path.exists(_f) is False:
        print(f'{_f} does not exist')
        return ''
    search_result = search_file(file=_f, patt=r'db/alias.db')
    _temp = re.findall(r'"RECORD=.*"', search_result)
    output = [re.sub(r'\"|\)|RECORD\=|ALIAS\=', '', s).split(',')
              for s in _temp]
    return [{'record': s[0], 'alias': s[-1]} for s in output]


def process_alias_template(parent_release: str, record: str,
                           alias: str) -> list[str]:
    """
    Opens the parent db/alias.db file and processes the
    substitutions.
    This is the second level of PV names (like in motor records).
    E.g. LM1K2:MCS2:01:m1 <--> LM1K2:INJ_MP1_MR1.RBV

    Parameters
    ----------
    parent_release : str
        Path to the parent IOC's release.
    record : str
        The EPICS record for substitution to generate PV names.
    alias : str
        The alias for the EPICS record.

    Returns
    -------
    list[str]
        DESCRIPTION.

    """

    _target_file = f'{parent_release}/db/alias.db'
    if os.path.exists(_target_file):
        with open(_target_file, encoding='utf-8') as _f:
            _temp = _f.read()
    else:
        print(f'{parent_release} does not exist')
        return None
    # remove the 'alias' prefix from the tuple
    _temp = re.sub(r'alias\(| +', '', _temp)
    _temp = re.sub(r'\)\s*\n', '\n', _temp)
    # then make the substitutions
    _temp = re.sub(r'\$\(RECORD\)', record, _temp)
    _temp = re.sub(r'\$\(ALIAS\)', alias, _temp)
    return [s.replace('"', '').split(',') for s in _temp.split()]


def show_temp_table(input_data: list, col_list: list):
    """
    Formats the 'disable' column in the find_ioc json output for clarity
    and prints the pretty table to the terminal.
    """
    # color code the disable state for easier comprehensions
    temp = copy.deepcopy(input_data)
    for _d in temp:
        if _d.get('disable') is not None:
            if _d.get('disable') is True:
                _d['disable'] = f'{Fore.LIGHTGREEN_EX}True{Style.RESET_ALL}'
        else:
            _d['disable'] = f'{Fore.RED}False{Style.RESET_ALL}'

    # prompt user for initial confirmation
    print(f'{Fore.LIGHTGREEN_EX}Found the following:{Style.RESET_ALL}')
    print(build_table(temp, col_list))


###############################################################################
# %% Argparser
###############################################################################
# parser obj configuration
parser = argparse.ArgumentParser(
    prog='gatherPVAliases',
    description="""gathers all record <-> alias associations from a child's
     ioc.cfg, st.cmd, and parent ioc.cfg.""",
    epilog='')
# main command arguments
parser.add_argument('patt', type=str)
parser.add_argument('hutch', type=str)
parser.add_argument('-d', '--dry_run', action='store_true',
                    default=False,
                    help='''Forces a dry run for the script.
                    No files are saved.''')

###############################################################################
# %% Main
###############################################################################


def main():
    """
    Main function entry point
    """
    # parse args
    args = parser.parse_args()
    # search ioc_cfg and build the dataset
    data = find_ioc(args.hutch, args.patt)
    if data is None:
        print(f'{Fore.RED}No results found for {Style.RESET_ALL}{args.patt}'
              + f'{Fore.RED} in{Style.RESET_ALL}'
              + f'{args.hutch}')
        sys.exit()

    # find the parent directories
    for _d in data:
        _d['parent_ioc'] = find_parent_ioc(_d['id'], _d['dir'])

    # Hard code the column order for the find_ioc output
    column_list = ['id', 'dir',
                   Fore.LIGHTYELLOW_EX + 'parent_ioc' + Style.RESET_ALL,
                   'host', 'port',
                   Fore.LIGHTBLUE_EX + 'alias' + Style.RESET_ALL,
                   Fore.RED + 'disable' + Style.RESET_ALL]
    if args.hutch == 'all':
        column_list = ['hutch'] + column_list
    show_temp_table(data, column_list)

    ans = simple_prompt('Proceed? (Y/n): ', default='Y')
    # Abort if user gets cold feet
    if ans is False:
        sys.exit()
    print(f'{Fore.RED}Skipping disabled child IOCs{Style.RESET_ALL}')

    # iterate through all the child ioc dictionaries
    for _ioc in data:
        if _ioc.get('disable') is not True:
            # first acquire the base alias dictionary
            alias_dicts = acquire_aliases(_ioc['dir'], _ioc['id'])
            # show the record aliases to the user
            print(Fore.LIGHTGREEN_EX
                  + 'The following substitutions were found in the st.cmd:'
                  + Style.RESET_ALL)
            print(build_table(alias_dicts, ['record', 'alias'], align='l'))
            # optional skip for all resulting PV aliases
            save_all = (simple_prompt(
                'Do you want to save save_all resulting PV aliases? '
                + 'This will generate '
                + Fore.LIGHTYELLOW_EX
                + f'{len(alias_dicts)}'
                + Style.RESET_ALL
                + ' files (y/N): '))

            # initialize a flag for skipping annoying prompts
            skip_all = None
            show_pvs = None

            # initialize a default file directory for dumping aliases
            default_dest = os.getcwd() + '/' + f"{_ioc['id']}_alias"

            # now iterate through the alias dicts for PV alias substitutions
            for i, a in enumerate(alias_dicts):
                # then iterate through all the PVs from root PV
                alias_list = process_alias_template(_ioc['parent_ioc'],
                                                    a['record'], a['alias'])
                # capture output based on 61 char max record name
                _output = [f"{al[0]:<61}{al[-1]:<61}" for al in alias_list]
                # Demonstrate PV aliases on first iteration
                if (i == 0) | ((show_pvs is True) & (skip_all is False)):
                    # show output to user, building a temp list of dict first
                    _temp = [{'PV': al[0], 'Alias': al[-1]}
                             for al in alias_list]
                    print(Fore.LIGHTGREEN_EX
                          + 'The following PV aliases are built:'
                          + Style.RESET_ALL)
                    print(build_table(_temp, ['PV', 'Alias'], align='l'))
                    del _temp

                # If doing a dry run, skip this block
                if args.dry_run is False:
                    # Respect the skip flag
                    if skip_all is True:
                        continue
                    # ask user for input
                    if save_all is False:
                        ans = (simple_prompt(
                            'Would you like to save this PV set? (y/N): '))
                        if ans is True:
                            # give the user an option to be lazy again
                            save_all = (simple_prompt(
                                        'Would you like to apply this for'
                                        + ' all subsequent sets? (y/N): '))
                            # Avoid some terminal spam using these flags
                            show_pvs = not save_all
                            skip_all = False
                        if ans is False:
                            skip_all = (simple_prompt(
                                'Skip all further substitutions? (Y/n): ',
                                default='Y'))
                            save_data = False
                            # Avoid some terminal spam using this flag
                            show_pvs = not skip_all
                            continue

                else:
                    # Set flags to surpress prompts during dry run
                    ans = False
                    save_data = False

                if save_all is True:
                    # only ask once
                    dest = (request_file_dest(
                        'Choose destination for data dump', default_dest))
                    save_data = True
                    save_all = None

                # else pester the user to approve for every single dataset
                elif (save_all is not None) & (ans is True):
                    dest = request_file_dest('Choose base file destination',
                                             default_dest)
                    save_data = True

                # write to file, else do nothing
                if (save_data is True) & (args.dry_run is False):
                    # make sure the destination exists and mkdir if it doesn't
                    if os.path.exists(dest) is False:
                        print(Fore.LIGHTBLUE_EX
                              + f'Making directory: {dest}' + Style.RESET_ALL)
                        os.mkdir(dest)
                    # pad leading 0 for file sorting
                    j = i
                    if i < 10:
                        j = '0'+f'{i}'
                    file_dest = dest + '/' + f"record_alias_{j}.txt"
                    with open(file_dest, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(_output))
                    default_dest = dest
                del _output

    sys.exit()


if __name__ == '__main__':
    main()
