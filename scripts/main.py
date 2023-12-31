from dataclasses import dataclass
from datetime import datetime
from io import TextIOWrapper
import itertools
from multiprocessing import shared_memory
import os
from typing import Callable, Iterable

POST_FOLDER = 'posts'
CATEGORY_FOLDER = 'categories'
DOCINFO_FOLDER = 'docinfo'
DOCINFO_FOOTER_FILENAME = 'docinfo-footer.html'
INDEX_FILENAME = 'index.adoc'


def to_what(filename: str, what: str) -> str:
    return f'{os.path.splitext(filename)[0]}-docinfo-{what}.html'

def to_header(filename: str) -> str: return to_what(filename, 'header')
def to_footer(filename: str) -> str: return to_what(filename, 'footer')


def get_from_content[T](
        lines: Iterable[str],
        attribute: str,
        parse: Callable[[str], T],
        default: Callable[[], T]) -> T:
    for line in lines:
        if line.startswith(attribute):
            return parse(line.removeprefix(attribute).strip())
    return default()


def do_with_lines_of_file[T](filename: str, do_with_content: Callable[[Iterable[str]], T]) -> T:
    with open(filename, 'r') as handle:
        return do_with_content(handle.readlines())


class AdocFile(object):

    def __init__(self, filename: str):
        self.filename: str = filename
        self.__read_meta_data()

    def __read_meta_data(self):

        def get_categories(line: str):
            return [category.strip() for category in line.split(',')]

        def throw(message: str):
            def inner():
                raise Exception(message)
            return inner

        with open(self.path, 'r') as handle:
            lines = handle.readlines()
            self.categories: Iterable[str] = get_from_content(lines, ':categories:', get_categories, lambda: [])
            self.creation_date: datetime = get_from_content(lines, ':creation-date:', lambda line: datetime.strptime(line, "%m/%d/%Y"), throw('Attribute :creation-date: must be present in post.'))
            self.title: str = get_from_content(lines, '=', lambda line: line, throw('Title must be present in post.'))


    @property
    def path(self) -> str:
        return os.path.join(POST_FOLDER, self.filename)

    @property
    def shared_header(self) -> str:
        return os.path.join(DOCINFO_FOLDER, to_header(self.filename))

    @property
    def shared_footer(self) -> str:
        return os.path.join(DOCINFO_FOLDER, to_footer(self.filename))


def find_all_post_files() -> Iterable[AdocFile]:
    for filename in os.listdir(POST_FOLDER):
        _, ext = os.path.splitext(filename)
        if ext == '.adoc':
            yield AdocFile(filename)


def format_category_for_html(cat: str, is_in_root: bool) -> str:
    category_file: str = os.path.join(CATEGORY_FOLDER, f'{cat}.html')
    return f'<a href="{'.' if is_in_root else '..'}/{category_file}" class="category">{cat}</a>'

def write_docinfo(file: AdocFile, categories: Iterable[str], is_in_root: bool):

    def write_to_handle(handle: TextIOWrapper):
        handle.write('<div class="garykl-frame">\n')
        handle.write('<div class="categories">\n')
        handle.write('<h3>Musings on Software Development</h3>\n')
        handle.write(f'Post from {file.creation_date.strftime('%B %d, %Y')}<br>\n')
        handle.write('Categories: ')
        handle.writelines(",\n".join([format_category_for_html(category, is_in_root) for category in categories]))
        handle.write('<br>\nby Gary Klindt\n')
        handle.write('</div>\n')
        handle.write('</div>\n')

    for path in [file.shared_header, file.shared_footer]:
        with open(path, 'w') as handle:
            write_to_handle(handle)

def write_plain_docinfo(filename: str, categories: Iterable[str], is_in_root: bool):

    def write_to_handle(handle: TextIOWrapper):
        handle.write('<div class="garykl-frame">\n')
        handle.write('<div class="categories">\n')
        handle.write('<h3>Musings on Software Development</h3>\n')
        handle.write(f'Blog last updated on {datetime.now().strftime('%B %d, %Y')}<br>\n')
        handle.write('Available categories: ')
        handle.writelines(",\n".join([format_category_for_html(category, is_in_root) for category in categories]))
        handle.write('<br>\nby Gary Klindt\n')
        handle.write('</div>\n')
        handle.write('</div>\n')

    for specialization in [to_header, to_footer]:
        with open(os.path.join(DOCINFO_FOLDER, specialization(filename)), 'w') as handle:
            write_to_handle(handle)


def format_date(date: datetime) -> str:
    return date.strftime('%Y, %B')


def write_adoc_list_file(filename: str, title: str, input_files: Iterable[AdocFile], is_in_root: bool):

    sorted_files = sorted(input_files, key=lambda file: file.creation_date)
    with open(filename, 'w') as handle:
        handle.write(':nofooter:\n')
        handle.write(':source-highlighter: rouge\n')
        handle.write(':rouge-style: monokai\n')
        handle.write(f'= {title}\n\n')

        grouped_files = itertools.groupby(sorted_files, key=lambda file: format_date(file.creation_date))
        for key, group in grouped_files:
            handle.write(f'== {key}\n\n')
            for file in group:
                handle.write(f'xref:{'.' if is_in_root else '..'}/{file.path}[{file.title}] `[{', '.join(file.categories)}]`\n\n')


def write_category_file(category: str, files: Iterable[AdocFile]) -> str:
    filename = f'{category}.adoc'
    write_adoc_list_file(os.path.join(CATEGORY_FOLDER, filename), category, files, False)
    return filename

def write_index_file(adoc_files: Iterable[AdocFile]) -> str:
    write_adoc_list_file(INDEX_FILENAME, 'Available posts', adoc_files, True)
    return INDEX_FILENAME

class CategoryFiles:
    
    def __init__(self):
        self.files: dict[str, list[AdocFile]] = {}

    def add_file(self, category: str, adoc_file: AdocFile):
        if category not in self.files:
            self.files[category] = []
        self.files[category].append(adoc_file)


if __name__ == '__main__':

    category_files = CategoryFiles()
    adoc_files = list(find_all_post_files())
    all_categories: Iterable[str] = [c for file in adoc_files for c in file.categories]

    for adoc_file in adoc_files:
        if adoc_file.categories is not None:
            write_docinfo(adoc_file, adoc_file.categories, is_in_root=False)

            for category in adoc_file.categories:
                category_files.add_file(category, adoc_file)

        summary = f'{adoc_file.filename}: {"-" if adoc_file.categories is None else ", ".join(adoc_file.categories)}'
        print(summary)

    for category, files in category_files.files.items():
        category_file = write_category_file(category, files)
        write_plain_docinfo(category_file, all_categories, is_in_root=False)

    index_file = write_index_file(adoc_files)
    write_plain_docinfo(index_file, all_categories, is_in_root=True)
