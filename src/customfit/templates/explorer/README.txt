What is this directory? We want to customize django-sqlexplorer, but it doesnt' really
give us the option of customizing it. So, we do an end-run around it: we put a customized template
here and our template-loader will load it *first* (before it looks in the app). So by putting a
template here, we shadow (and customize) the app ourselves.
