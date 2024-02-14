********
database
********

Introduction
------------

JWQL uses the django database models for creating tables, updating table fields, adding 
new data to tables, and retrieving data from tables. For instrument monitors, in particular,
there are a number of issues that may be relevant.

In general, django model documentation can be found 
`on the django website <https://docs.djangoproject.com/en/5.0/#the-model-layer>`_. 
Unfortunately, finding a particular bit of documentation in django can be a challenge, so
a few quick-reference notes are provided below.

Retrieving Data
---------------

Django retrieves data directly from its model tables. So, for example, if you want to 
select data from the `MIRIMyMonitorStats` table, you must first import the relevant 
object:

.. code-block:: python

    from jwql.website.apps.jwql.monitor_models.my_monitor import MIRIMyMonitorStats

Then, you would access the database contents via the `objects` member of the class. For 
example, to search the `MIRIMyMonitorStats` table for all entries matching a given 
aperture, and to sort them with the most recent date at the top, you might do a query like
the following:

.. code-block:: python

    aperture = "my_miri_aperture"
    
    records = MIRIMyMonitorStats.objects.filter(aperture__iexact=aperture).order_by("-mjd_end").all()

In the above code,

* The `filter()` function selects matching records from the full table. You can use 
  multiple filter statements, or a single filter function with multiple filters. `filter()`
  statements are always combined with an implicit AND.
* If you have a long filter statement and want to separate it from the query statement,
  you can create a dictionary and add it in with the `**` prepended. The dictionary 
  equivalent to the above would be `{'aperture__iexact': aperture}`
* The text before the double underscore is a field name, and the text afterwards describes
  the type of comparison. `iexact` indicates "case-insensitive exact match". You can also
  use a variety of standard SQL comparisons (`like`, `startswith`, `gte`, etc.)
* If you want to get only records that *don't* match a pattern, then you can use the 
  `exclude()` function, which otherwise operates exactly the same as `filter()`.
* In the `order_by()` function, the `-` at the start is used to reverse the sort order, 
  and the `mjd_end` is the name of the field to be sorted by.
* The `all()` statement indicates that you want all the values returned. `get()` returns
  a single value and can be iterated on, `first()` returns only the first value, etc.

As an example of multiple filters, the code below:

.. code-block:: python

    records = MIRIMyMonitorStats.objects.filter(aperture__iexact=ap, mjd_end__gte=60000)
    
    filters = {
        "aperture__iexact": ap,
        "mjd_end__gte": 60000
    }
    records = MIRIMyMonitorStats.objects.filter(**filters)

show two different ways of combining a search for a particular aperture *and* only data 
taken more recently than MJD=60000.

Note that django executes queries lazily, meaning that it will only actually *do* the 
query when it needs the results. The above statement, for example, will not actually 
run the query. Instead, it will be run when you operate on it, such as

* Getting the length of the result with e.g. `len(records)`
* Printing out any of the results
* Asking for the value of one of the fields (e.g. `records[3].aperture`)

Q Objects
=========

In order to make more complex queries, Django supplies "Q Objects", which are essentially 
encapsulated filters which can be combined using logical operators. For more on this, see
`the django Q object documentation <https://docs.djangoproject.com/en/5.0/topics/db/queries/#complex-lookups-with-q-objects>`_.

Storing Data
------------

Django also uses the model tables (and objects) directly for storing new data. For example,
if you have a monitor table defined as below:

.. code-block:: python

    from django.db import models
    from django.contrib.postgres.fields import ArrayField

    class NIRISSMyMonitorStats(models.Model):
        aperture = models.CharField(blank=True, null=True)
        mean = models.FloatField(blank=True, null=True)
        median = models.FloatField(blank=True, null=True)
        stddev = models.FloatField(blank=True, null=True)
        counts = ArrayField(models.FloatField())
        entry_date = models.DateTimeField(blank=True, null=True)

        class Meta:
            managed = True
            db_table = 'niriss_my_monitor_stats'
            unique_together = (('id', 'entry_date'),)
            app_label = 'monitors'

then you would create a new entry as follows:

.. code-block:: python

    values = {
        "aperture": "my_aperture",
        "mean": float(mean),
        "median": float(median),
        "stddev": float(stddev),
        "counts": list(counts.astype(float)),
        "entry_date": datetime.datetime.now()
    }
    
    entry = NIRISSMyMonitorStats(**values)
    entry.save()

There are (as usual) a few things to note above:

* Django doesn't have a built-in array data type, so you need to import it from the 
  database-compatibility layers. The ArrayField takes, as a required argument, the type
  of data that makes up the array.
* In the Meta sub-class of the monitor class, the `all_label = 'monitors'` statement is 
  required so that django knows that the model should be stored in the monitors table.
* The `float()` casts are required because the database interface doesn't understand 
  numpy data types.
* The `list()` cast is required because the database interface doesn't understand the 
  numpy `ndarray` data type
