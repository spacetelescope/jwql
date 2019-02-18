# Using the `webpage-template` branch to develop a webpage

The `webpage-template` branch includes a number of template files and functions. These are designed to make it easier for a contributor who is unfamiliar with web development to write a new page for the web application. They includes the following:

| Template File/Function | Description | Location |
| ---------------------- | ----------- | -------- |
| HTML template   | file containing HTML used to render web page content (text, links, photos, tables, etc.) | `jwql/website/apps/jwql/templates/WEBPAGE_TEMPLATE.html` |
| view function template | python function that passes data to an HTML template | `WEBSITE_TEMPLATE()` in `jwql/website/apps/jwql/views.py` |
| URL entry template  | list item that maps a URL to a view | `jwql/website/apps/jwql/urls.py`

* Interfaces to the existing `monitor_template` to demonstrate how the web app and package connect



*To learn more about topics like HTML templates, views, and URLs, see the [JWQL intro to web apps](https://github.com/spacetelescope/jwql/blob/master/presentations/JWQL_web_app.pdf).*

-----------------

## How to view the template content

1. Make sure you have a fork of the `jwql` repo that points to `spacetelescope/jwql` as `upstream`. (See the [contribution guide](https://github.com/spacetelescope/jwql/wiki/git-&-GitHub-workflow-for-contributing) if you need to set this up.)

1. Create a copy of the `webpage-template` branch:

    ```bash
    git checkout -b <your_desired_branch_name> upstream/webpage-template
    ```

1. Activate your [`jwql` virtual environment](https://github.com/spacetelescope/jwql#environment-installation):

    ```bash
    source activate jwql
    ```

1. Start a remote server to run the web app:

    ```bash
    python jwql/website/manage.py runserver
    ```

1. Open the template web page in your browser: http://127.0.0.1:8000/webpage_template


## How to customize the template content


