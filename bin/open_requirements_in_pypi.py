import os.path
import re
import webbrowser


def open_requirements_file():
    curr_file_path = os.path.dirname(__file__)
    req_file_path = os.path.join(curr_file_path, "../requirements.txt")
    f = open(req_file_path, "r")
    return f


def get_packages_from_requirements(req_file):
    return_me = []
    req_line_re = re.compile("^([^=]+)==")
    for line in req_file:
        match_obj = req_line_re.search(line)
        if match_obj:
            package_name = match_obj.group(1)
            return_me.append(package_name)

    return return_me


def open_tabs(package_name_list):
    url_prefix = "https://pypi.python.org/pypi/"
    initial_window = True
    for package_name in package_name_list:
        full_url = url_prefix + package_name
        if initial_window:
            webbrowser.open(full_url, new=1)
        else:
            webbrowser.open(full_url, new=2)
        initial_window = False


def main():
    reqirements_file = open_requirements_file()
    package_names = get_packages_from_requirements(reqirements_file)
    open_tabs(package_names)
    reqirements_file.close()


if __name__ == "__main__":
    main()
