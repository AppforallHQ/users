$(document).ready(function(){
    cur_path = window.location.pathname;
    tab_links = $("#the-side>ul>li>a");
    for(var i=0; i<tab_links.length; i++){
        cur_tab = $(tab_links[i]);
        if(cur_tab.attr('href') === cur_path){
            cur_tab.parent().addClass("active").siblings().removeClass("active");
        }
    }
});
