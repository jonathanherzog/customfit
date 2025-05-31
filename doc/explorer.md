SQL explorer:

django-SQL-explorer (https://github.com/groveco/django-sql-explorer) is an awesome package
that lets us quickly pull out data for ad-hoc quick-and-dirty reports. However, it does not come
with any good graphing/charting facilities, and does not have the ability to turn them on or add them
easily. This is a shame, since the underlying Javascript library it uses for pivot tables 
(https://github.com/nicolaskruchten/pivottable) can easily include Google charts. So what to do?

We add Google Charts ourselves by:

* Modifying sql-explorer's javascript (explorer.js, which calls pivottable.js) and putting it
    in our static directory (js/explorer/explorer-with-google-charts.js)

* Modifying the default template for explorer and putting it in our templates directory (where
    it gets found by the template-loader before the app's actual template), and
    
* Modifying the default template to call Google charts and our modified javascript.
 
* And for good measure, extending the template's footer to remind us of the modification. With luck, this
   will keep of from wasting TOO much time chasing bugs in the app instead of our modification.
   
   
Enjoy!

