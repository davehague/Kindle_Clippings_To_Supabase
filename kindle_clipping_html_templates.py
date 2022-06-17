from string import Template

PAGE = Template('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>$book_title</title>
    <meta name="description" content="$book_title">
    <meta name="author" content="$book_author">
    <style>
        body {
            font-family: Arial, Helvetica, sans-serif;
        }
        header {
            text-align: center;
        }
        li {
            list-style: none; 
        }
        blockquote {
            background: #f1f1f1;
            margin-top: 10px;
            padding: 10px;
            font-style: italic;
            line-height: 1.25;
        }
        blockquote span {
            color: #7e7e7e;
            font-size: 0.6em;
            display: block;
            padding-top: 20px;
        }
    </style>
</head>
<body>
    <!-- Page Header -->
    <header>
        <h1>$book_title</h1>
        <h2>by $book_author</h2>
        <p>Highlights as of $file_datetime</p>
    </header>
    
    <!-- Highlights Section -->
    <section>
        $book_highlights
    </section>
</body>
</html>''')

HIGHLIGHT = Template('''
        <li>
            <blockquote>
                $text
                <span>($location, $datetime)</span>
            </blockquote>
        </li>''')
