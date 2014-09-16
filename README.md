# ReQL command line interface

Run [RethinkDB](http://rethinkdb.com/) [ReQL](http://rethinkdb.com/docs/introduction-to-reql/) commands in the terminal.

Makes it easy to both look at your data in a nice colorized format.

If you pipe the output to another program, it turns off the colors and
condenses the JSON to one document per line for easy processing with
other tools like [jq](http://stedolan.github.io/jq/)

## Installation

```bash
$ pip install reql_cli
```

## Usage

```
$ rql --help
usage: rql [-h] [--port PORT] [--host HOST] [--auth_key AUTH_KEY] [--db DB]
           [--pagesize PAGESIZE] [--style STYLE] [--array] [--newline]
           [--color] [--auto]
           QUERY

Run ReQL commands in the terminal. If the output is being piped, will print
one document per line and not use color

positional arguments:
  QUERY                 ReQL query to run

optional arguments:
  -h, --help            show this help message and exit
  --port PORT, -p PORT  RethinkDB driver port
  --host HOST, -t HOST  RethinkDB host address
  --auth_key AUTH_KEY, -k AUTH_KEY
                        RethinkDB auth key
  --db DB, -d DB        default database for queries
  --pagesize PAGESIZE, -g PAGESIZE
                        Documents per page. No effect on piped output
  --style STYLE, -s STYLE
                        Source code color scheme. Valid values: monokai,
                        manni, rrt, perldoc, borland, colorful, default,
                        murphy, vs, trac, tango, fruity, autumn, bw, emacs,
                        vim, pastie, friendly, native
  --array, -a           Force JSON array output
  --newline, -n         Force one document per line output
  --color, -c           Force color/pretty printed output
  --auto                Decide output format based on whether output is being
                        piped (this is the default)
```

## Examples:

Create a new table:

```bash
$ rql 'r.table_create("posts")'
{
    "created": 1
}

Ran:
 r.table_create('posts')
```

Slurp in data from some api:

```bash
$ rql 'r.table("posts").insert(r.http("jsonplaceholder.typicode.com/posts"))'
{
    "deleted": 0,
    "errors": 0,
    "inserted": 100,
    "replaced": 0,
    "skipped": 0,
    "unchanged": 0
}

Ran:
 r.table('posts').insert(r.http('jsonplaceholder.typicode.com/posts'))
```

Page through your nice pretty data:

```bash
$ rql --pagesize=2 'r.table("posts").without("body")'
{
    "id": 2,
    "title": "qui est esse",
    "userId": 1
}

{
    "id": 15,
    "title": "eveniet quod temporibus",
    "userId": 2
}

[2] Hit any key to continue (or q to quit)...
```

Piping it out to another process compacts the data for machine
consumption (one document per line, no extraneous spaces):

```bash
$ rql 'r.table("posts").without("body").limit(5)' | cat
{"userId":1,"id":1,"title":"sunt aut faceret"}
{"userId":1,"id":4,"title":"eum et est occaecati"}
{"userId":1,"id":2,"title":"qui est esse"}
{"userId":1,"id":6,"title":"dolorem eum magni eos aperiam quia"}
{"userId":1,"id":7,"title":"magnam facilis autem"}
```

You can also force the output to be a valid json array with `--array`:

```bash
$ rql --array 'r.table("posts")("id").limit(5)'
[1,4,2,6,7]
```

Note: this format doesn't emit newlines

## OK, that's pretty great. What else?

Uhh, you could use your RethinkDB server as a calculator if you want:

```bash
$ rql 'r.expr(1) + 3 + (r.expr(4) * 3)'
16

Ran:
 r.expr(1) + 3 + (r.expr(4) * 3)
```

## Bugs

Report bugs or feature requests on
[github](http://github.com/deontologician/reql_cli/issues)
