```html
{% if page.toc==true %}
<div class="container">  
    <div class="contents">  
        {{ page.content }}
    </div>   
    <div class="table-of-contents">
    <aa>Contents</aa>
    {% include toc.html html=content %}
</div>
</div>
{% else %}
{{ page.content }}
{% endif %}
```