import config
import hashlib
import re
import os
from datetime import datetime
import argparse
from supabase import create_client, Client

from kindle_clipping_html_templates import PAGE, HIGHLIGHT

HIGHLIGHT_SEPARATOR = "=========="
OUTPUT_DATE_FORMAT = "%d/%m/%y %H:%M:%S"


########################################################################################################################
class Book:
    book_titles = set()  # maintain a set of book titles

    ####################################################################################################################
    def __init__(self, title, author):
        self.title = Book.tidy_title(title)
        Book.book_titles.add(self.title)  # add book to list of known books
        self.author = author
        self.highlights = []

    ####################################################################################################################
    def add_highlight(self, highlight):
        if highlight:
            self.highlights.append(highlight)

    ####################################################################################################################
    def highlights_to_html(self):
        # iterate over all highlights creating HTML for each
        for highlight in self.highlights:
            yield HIGHLIGHT.safe_substitute({
                'text': highlight.content,
                'location': highlight.main_loc,
                'datetime': highlight.date
            })

    ####################################################################################################################
    def write_book_to_supabase(self):
        supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

        len_highlights = len(self.highlights)
        counter = 1
        for highlight in self.highlights:
            print("Checking highlight" + str(counter) + " of " + str(len_highlights))
            highlight_hash = highlight.to_hash()
            data = supabase.table("clippings") \
                .select("hash") \
                .filter("hash", "eq", highlight_hash) \
                .execute()

            if len(data.data) == 0:
                data = supabase.table("clippings").insert({
                    "hash": highlight_hash,
                    "title": self.title,
                    "author": self.author,
                    "highlight_type": highlight.highlight_type,
                    "main_loc": highlight.main_loc,
                    "content": highlight.content,
                    "timestamp": convert_date_to_iso(highlight.date)
                }).execute()

            counter += 1

    ####################################################################################################################
    def write_book_to_html(self):
        """Writes all book attributes to a HTML file."""
        # get filename from book title and output file extension
        filename = "{}.html".format(self.title)

        # get all the highlights as HTML
        highlights_html = self.highlights_to_html()

        # get current datetime in our format
        datetime_now = datetime.now().strftime(OUTPUT_DATE_FORMAT)

        # write the book to HTML
        with open(filename, 'w', encoding="utf-8") as book_file:
            book_file.write(PAGE.safe_substitute({
                'book_title': self.title,
                'book_author': self.author,
                'file_datetime': datetime_now,
                'book_highlights': '\n'.join(list(highlights_html))
            }))
            # give status prompt to user
            print(f"HTML file produced for: {self.title}")

    ####################################################################################################################
    @staticmethod
    def tidy_title(raw_title):
        """ Removed unwanted characters from the highlight title. """
        # remove chars tht are not alphanumeric or ; , _ - . ( ) ' "
        title = re.sub(r"[^a-zA-Z\d\s;,_\-\.()'\"]+", "", str(raw_title))
        # Trim off anything that isn't a word at the start & end
        title = re.sub(r"^\W+|\W+$", "", title)
        return title

########################################################################################################################


class Highlight:
    """ Represents a Highlight within a Book and its attributes. """

    ####################################################################################################################
    def __init__(self, raw_highlight_str):
        # (title, author, highlight_type, main_loc, date, content)
        self.title, self.author, self.highlight_type, self.main_loc, self.date, self.content = \
            Highlight.parse_highlight(raw_highlight_str)

    def to_hash(self):
        return hashlib.sha1(self.content.encode('utf-8')).hexdigest()
        # return hash((self.title, self.author, self.main_loc))

    ####################################################################################################################
    @staticmethod
    def tidy_date(raw_date):
        """ Tidies a clipping date into our desired format. """
        # remove unwanted preface
        date_str = raw_date.replace('Added on ', '')
        # expected date_str: Wednesday, October 24, 2018 10:25:36 PM
        # https://pythonexamples.org/python-datetime-format/
        input_date_format = '%A, %B %d, %Y %H:%M:%S %p'
        datetime_object = datetime.strptime(date_str, input_date_format)
        return datetime_object.strftime(OUTPUT_DATE_FORMAT)

    ####################################################################################################################
    @staticmethod
    def get_type_and_location(loc_str):
        """ Expected values:
            - Your Highlight on Location 6105-6113
            - Your Note on page 57 | Location 866
        """
        loc_str = loc_str.replace("- Your ", "").strip();
        type_and_location = loc_str.split(" on ")
        highlight_type = type_and_location[0]

        page_and_location = type_and_location[1].split(" | ")
        if len(page_and_location) == 1:
            highlight_location = page_and_location[0]
        else:
            highlight_location = page_and_location[1]

        return highlight_type.strip(), highlight_location.strip()

    ####################################################################################################################
    @staticmethod
    def parse_highlight(raw_highlight_str):
        """Parses a raw highlight string into a Highlight object.

        Returns:
            (title, author, highlight_type, main_loc, date, content)
        """
        empty_set = (None, None, None, None, None, None)

        # split the highlight up by line
        split_str = raw_highlight_str.split('\n')
        # ensure has enough lines
        if len(split_str) < 5:
            return empty_set

        # determine if we are not on the first clipping in the file
        if split_str[0] == '':
            # remove the first split as it was a separator originally
            split_str = split_str[1:]

        # get book title and author
        book_details = split_str[0]
        # get last content in round brackets
        book_details_split = re.search(r"\(([^)]*)\)[^(]*$", book_details)
        if book_details_split:
            # get the title and author from the split result
            title = Book.tidy_title(book_details[:book_details_split.start()])
            author = book_details_split.group(1)
        else:
            return empty_set

        # get highlight details
        highlight_details = split_str[1]
        highlight_details_split = highlight_details.split(" | Added on ")
        if highlight_details_split:
            # get the main location and highlight date from the split result

            type_and_location = Highlight.get_type_and_location(highlight_details_split[0])
            highlight_type = type_and_location[0]
            main_loc = type_and_location[1]

            date = highlight_details_split[1]

        else:
            return empty_set

        # tidy our date up into our desired format
        date = Highlight.tidy_date(date)

        # get the highlight content
        content = '\n'.join(split_str[3:-1])

        return title.strip(), \
            author.strip(), \
            highlight_type.strip(), \
            main_loc.strip(), \
            date, \
            content.strip()

########################################################################################################################


def convert_date_to_iso(datestring):
    return datetime.strptime(datestring, OUTPUT_DATE_FORMAT).isoformat()


def process(clippings_file_path, output_dir_path):
    processed_books = []
    library = []

    # move to the cwd
    cwd = os.getcwd()
    os.chdir(cwd)
    # create output folder if not exists
    if not os.path.exists(output_dir_path):
        os.mkdir(output_dir_path)

    # reset knowledge of book titles
    Book.book_titles = set()

    # read in the clippings
    with open(clippings_file_path, "r", encoding='utf-8') as clippings_file:
        file_contents = clippings_file.read()

    # move to the output directory
    os.chdir(output_dir_path)

    # split all the highlights up into a list
    highlights = file_contents.split(HIGHLIGHT_SEPARATOR)

    # process each highlight
    for raw_str in highlights:
        h = Highlight(raw_str)
        # if haven't seen the book title before create a new book, then add the highlight
        if (not h.title is None) and (h.title not in Book.book_titles):
            b = Book(h.title, h.author)
            b.add_highlight(h)  # add highlight to book
            library.append(b)  # add the new book to our library
        else:
            # check all other books we know about to add highlight to its own book
            for b in library:
                if b.title == h.title:
                    b.add_highlight(h)

    # process each book in our library
    for book in library:
        if book.title:
            # if we haven't processed the book, process now
            if book.title.strip() not in processed_books:
                # book.write_book_to_html()
                book.write_book_to_supabase();
                processed_books.append(book.title.strip())  # add the book as processed
            else:
                print(f"HTML file already produced for: {book.title}")


def generate_supabase_user():
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    user = supabase.auth.sign_up(email=config.SUPABASE_USER, password=config.SUPABASE_USER_PW)


########################################################################################################################


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--clippings_file_path", help="The path to the Kindle clippings text file.", \
                        default="./My Clippings.txt")
    parser.add_argument("-o", "--output_dir_path", help="The path for the output directory.", \
                        default="./output/")
    args = parser.parse_args()

    process(args.clippings_file_path, args.output_dir_path)
    # generate_supabase_user()
