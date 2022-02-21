# Using the `webpage-template` branch to develop a webpage

The `webpage-template` branch includes template code - files and functions - that are designed to make it easier for a contributor who is unfamiliar with web development to write a new page for the JWQL web application.

These template resources both 1) make up a kind of webpage-skeleton that can be used as a foundation and built upon and 2) contain example code that is hopefully useful.

The files and functions on the `webpage-template` branch that are designed to be edited are the following:

| Template File/Function | Description | Location |
| ---------------------- | ----------- | -------- |
| **HTML template**   | file containing HTML used to render web page content (text, links, photos, tables, etc.) | `jwql/website/apps/jwql/templates/WEBPAGE_TEMPLATE.html` |
| **view function template** | python function that passes data to an HTML template | `website_template()` in `jwql/website/apps/jwql/views.py` |
| **URL entry template**  | list item that maps a URL to a view | `jwql/website/apps/jwql/urls.py` |
| **data container function**  | python function that manipulates data for the view function | `website_template_data()` in `jwql/website/apps/jwql/data_containers.py` |

*To learn more about topics like HTML templates, views, and URLs, see the [JWQL intro to web apps](https://github.com/spacetelescope/jwql/blob/main/presentations/JWQL_web_app.pdf).*



## How to view the template content

1. Make sure you have a fork of the `jwql` repo that points to `spacetelescope/jwql` as `upstream`. (See the [contribution guide](https://github.com/spacetelescope/jwql/wiki/git-&-GitHub-workflow-for-contributing) if you need to set this up.)

1. Create a copy of the `webpage-template` branch and set it up to push to your fork:

    ```
    git checkout -b <your_desired_branch_name> upstream/webpage-template
    git push -u origin <your_desired_branch_name>
    ```

1. Activate your [`jwql` virtual environment](https://github.com/spacetelescope/jwql#environment-installation):

    ```bash
    source activate jwql
    ```

1. Start a local server to run the web app:

    ```bash
    python jwql/website/manage.py runserver
    ```

1. Open the template web page in your browser: http://127.0.0.1:8000/webpage_template


## How to customize the template content

*Even though we present these as separate steps here, don't take them as strictly chronological. It is often easiest to edit a webpage's HTML, view, and supporting functions all at the same time, so you can see how they affect one another.*

### 1. Update `urls.py` to point to the desired URL
- Change the string and the `name=` argument in the `path()` function to be the desired URL name.

- If you want to make a nested URL, (e.g. `miri/my_web_page`), look at other URLs in `urls.py` for examples.

- Be sure to check that the paths are ordered such that the [URL dispatcher](https://docs.djangoproject.com/en/2.1/topics/http/urls/#example) can find them all correctly. Reorder them if this is not the case!

### 2. Update the view and data container functions

- Update the `data_containers.webpage_template_data()` function to be useful to you. Read in the contents of files, query the MAST archive, or use the functions in the `jwql` package! Be sure to `return` the data you need so that it is easily accessible with a function call.

- Import this data in `views.webpage_template()`. Add any new entries to the `context` dictionary so your data will be passed to your HTML web page.

- Change the data container function name in `data_containers.py` to a more descriptive name than `webpage_template_data()`, and be sure to change the import statement and function calls in `views.py` to match your new function name.

- Change the view function name in `views.py` to a more descriptive name than `webpage_template()`, and be sure to change the entry in `urls.py` to match your new view name.

### 3. Update the HTML template

- Play around with `WEBPAGE_TEMPLATE.html` to display the information that you have passed in from `views.py`. If you are confused about how to access your data and structure the template, take a look at the [Jinja template documentation](http://jinja.pocoo.org/docs/2.10/templates/). Don't be afraid to add new text, links, buttons, or Bokeh plots. Use the local server that you set up above to see the changes you make in your browser.

- Change the HTML template name to a more descriptive name than `WEBPAGE_TEMPLATE.html`. Be sure to change the `template` variable in your view to match your new template name.

### 4. Share your work!
- When you are ready to share your new page to the JWQL team for review, follow the directions on our [Contribution Guide](https://github.com/spacetelescope/jwql/wiki/git-&-GitHub-workflow-for-contributing) to submit a pull request.



## Helpful Resources for Web Development
- HTML Documentation and Examples: https://www.w3schools.com/html/default.asp
- CSS Documentation and Examples: https://www.w3schools.com/css/default.asp
- Bootstrap Documentation: https://getbootstrap.com/docs/4.3/getting-started/introduction/
- Jinja2 HTML Template Documentation: http://jinja.pocoo.org/docs/2.10/templates/



*If you have questions about any part of this guide, please contact lchambers@stsci.edu and bourque@stsci.edu.*