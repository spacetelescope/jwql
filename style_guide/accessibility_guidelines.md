Guidelines for Accessible Development
=====================================

This document serves as a guide for developing accessible web pages and code within the `jwql` project.  Any contribution to the `jwql` code repository should be checked against these guidelines to ensure it meets all applicable standards. Any violations of these guidelines should be fixed before the code is committed to the `main` or `develop` branches. 


`jwql`-specific Guidelines
--------------------------

We have compiled below those WCAG 2.1 guidelines (see the "Resources" section below for more detail about WCAG) that are most directly applicable to the JWQL web app.

Every contribution to the web application must include the following features:

- Images and Plots
    - Write descriptive `alt` and `title` attributes in `<img>` tags
    - Use color schemes that are still meaningful to individuals with color blindness (see note below about Color Oracle)
    - When plotting data, use both colors AND symbols to distinguish datasets
    - Avoid using images of text
- Text
    - Ensure sure headers are in order (i.e. `<h1>` before `<h2>`, `<h2>` before `<h3>`, etc.) and do not skip (i.e. `<h3>` comes after `<h2>`, not `<h1>`)
    - Don't write explicit navigation instructions involving placement or direction (e.g. "in the upper right corner")
    - Differentiate links from normal text (different color and/or underline)
    - Describe the link purpose in link text (e.g. avoid using "here" as link text)
- Forms
    - Use `<fieldset>` tags to group related form fields
    - Describe form field values in/next to form, and/or provide default values
- Formatting
    - Ensure the page is still readable and functional when the text size is doubled
    - Ensure users can navigate through page with just the keyboard and not get trapped
    - Ensure you can see where you are when tabbing through page (e.g. buttons and links are highlighted when in focus)
    - Add informative page titles

Please note that this list is not exhaustive; other guidelines listed by WCAG or 508 may also apply to particular web pages and features and should be implemented as appropriate.


Resources
---------

The above guidelines are taken from the following guides and checklists that compile important components of an accessible web site: 

- [Web Content Accessibility Guidelines (WCAG)](https://www.w3.org/WAI/standards-guidelines/wcag/) - aims to provide a "single shared standard for web content accessibility that meets the needs of individuals, organizations, and governments internationally" and "explain how to make web content more accessible to people with disabilities."
- [Section 508 Standards](https://www.section508.gov/create) - the US Access Board's "accessibility requirements for information and communication technology (ICT) covered by Section 508 of the Rehabilitation Act and Section 255 of the Communications Act."

We especially recommend consulting WebAIM's [WCAG 2 Checklist](https://webaim.org/standards/wcag/checklist) for accessible design. [WebAIM](https://webaim.org/) is a site with many resources for designing accessible web applications that includes guidelines and examples.

In order to test how accessible your web page is, we recommend using the following resources:
- [Color Oracle](https://colororacle.org/) - free color-blindness simulator that alters the computer screen to demonstrate different varieties of color-blindness.
- [ChromeVox](https://chrome.google.com/webstore/detail/chromevox/kgejglhpjiefppelpmljglcjbhoiplfn?hl=en) - screen reader extension for Google Chrome browsers that allows users to explore web pages using only the keyboard.

*STScI Internal Only:* For more resources on web accessibility, check out OPO's Innerspace page on [Accessibility and 508 Compliance](https://innerspace.stsci.edu/display/A5C/Accessibility+and+508+Compliance).
