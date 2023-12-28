from dataclasses import dataclass
from multiprocessing import shared_memory
import os
from typing import Callable, Iterable

POST_FOLDER = 'posts'
CATEGORY_FOLDER = 'categories'
DOCINFO_FOLDER = 'docinfo'
DOCINFO_FOOTER_FILENAME = 'docinfo-footer.html'


def to_what(filename: str, what: str) -> str:
    return f'{os.path.splitext(filename)[0]}-docinfo-{what}.html'

def to_header(filename: str) -> str: return to_what(filename, 'header')
def to_footer(filename: str) -> str: return to_what(filename, 'footer')


@dataclass
class AdocFile:
    filename: str

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


def get_categories_from_content(lines: Iterable[str]) -> Iterable[str] | None:
    for line in lines:
        if ':categories:' in line:
            return [category.strip() for category in line.removeprefix(':categories:').strip().split(',')]


def do_with_lines_of_file[T](filename: str, do_with_content: Callable[[Iterable[str]], T]) -> T:
    with open(filename, 'r') as handle:
        return do_with_content(handle.readlines())


def write_docinfo(file: AdocFile, categories: Iterable[str]):

    def integrate_category(cat: str) -> str:
        category_file: str = os.path.join(CATEGORY_FOLDER, f'{cat}.html')
        return f'<a href="../{category_file}" class="category">{cat}</a>'

    with open(file.shared_header, 'w') as handle:
        handle.writelines(",\n".join([integrate_category(category) for category in categories]))


def write_category_file(category: str, files: Iterable[AdocFile]):
    with open(os.path.join(CATEGORY_FOLDER, f'{category}.adoc'), 'w') as handle:
        handle.write(f'= {category}\n\n')
        for file in files:
            handle.write(f'xref:../{file.path}[{file.filename}]\n\n')


class CategoryFiles:
    
    def __init__(self):
        self.files: dict[str, list[AdocFile]] = {}

    def add_file(self, category: str, adoc_file: AdocFile):
        if category not in self.files:
            self.files[category] = []
        self.files[category].append(adoc_file)


if __name__ == '__main__':

    category_files = CategoryFiles()

    for adoc_file in find_all_post_files():
        categories = do_with_lines_of_file(adoc_file.path, get_categories_from_content)
        if categories is not None:
            write_docinfo(adoc_file, categories)

            for category in categories:
                category_files.add_file(category, adoc_file)

        summary = f'{adoc_file.filename}: {"-" if categories is None else ", ".join(categories)}'
        print(summary)

    for category, files in category_files.files.items():
        write_category_file(category, files)
