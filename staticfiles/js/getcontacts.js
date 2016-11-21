var currentPage = 0;
var pageCount = 0;
var pageLen = 10;

function fadeOutErrorAlert(){
    setTimeout(function(){
        $('.slide-error').fadeOut();
    },5000);
};

function fadeOutSuccessAlert(){
    setTimeout(function(){
        $('.slide-success').fadeOut();
    },5000);

};

$(document).ready(function(){
    var $loader = $("#loader");

    OAuth.initialize('AUTH_KEY');
    var yahooData = function(auth){
        return auth.get("https://social.yahooapis.com/v1/me/guid?format=json");
    };

    var getYahooContacts = function(data){
        var guid = data.guid.value;
        var yahoo = OAuth.create('yahoo');
        return yahoo.get("https://social.yahooapis.com/v1/user/" + guid + "/contacts?format=json&count=max");
    };

    var getGoogleContacts = function(auth){
        return auth.get("https://www.google.com/m8/feeds/contacts/default/full?alt=json&max-results=500");
    };

    var parseGoogleContacts = function(data){
        var contacts = data.feed.entry;
        var result = [];
        contacts.forEach(function(item){
            if(item.gd$email){
                var email = item.gd$email[0].address,
                    name = item.title.$t;
                if(name){
                    result.push({name: name, email: email});
                }
            }
        });
        return result;
    };

    var invite = function(contacts){
        $loader.show();
        $.ajax({
            url: "/panel/invite/",
            data: {contacts: JSON.stringify(contacts)},
            type: "POST",
            dataType: "json",
        }).done(function(data){
            if(data.done == true){
                $(".slide-success").html("درخواست شما با موفقیت انجام شد.").show();
                cleanup();
                fadeOutSuccessAlert();
            }else{
                $(".slide-error").html("متاسفانه مشکلی در انجام درخواست شما رخ داده لطفا لحظاتی دیگر مجددا تلاش کنید.").show();
                fadeOutErrorAlert();
            }
            $loader.hide();
        });
    };

    var parseYahooContacts = function(data){
        var contacts = data.contacts.contact;
        var result = [];
        contacts.forEach(function(item){
            var fields = item.fields;
            var name, email;
            for(var i = 0; i < fields.length; i++){
                if(fields[i].type === "name"){
                    name = fields[i].value.givenName + " " + fields[i].value.familyName;
                    break;
                }
            }
            if(name){
                fields.forEach(function(eobj){
                    if (eobj.type === "email"){
                        email = eobj.value;
                        result.push({name: name, email: email});
                    }
                });
            }
        });
        return result;
    };

    var set_list = function(data){
        $(".emails-list-table").find("tr").remove();
        data.forEach(function(item){
            var template = "<tr class='enable'>" +
                    "<td class='name'>" + item.name + "</td>" +
                    "<td class='email'>" + item.email + "</td>" +
                    "<td class='check'><input type='checkbox'></td>";
            $(".emails-list-table").append(template);
            // Show table
            $(".emails-list-box").show();
            $(".email-invite-link").show();
            currentPage = 0;
            $table.trigger('repaginate');
        });
        var noResultText = "<tr id='error' style='display:none;'><td class='name' style='text-align:center'>متاسفانه نتیجه‌ای یافت نشد.</td></tr>";
        $(".emails-list-table").append(noResultText);
        // Bind table row click events
        bindTRowClicks();
    };

    var cleanup = function(){
        $(".emails-list-table").find("tr").remove();
        $(".emails-list-box").fadeOut('fast');
        $(".email-invite-link").fadeOut('fast');
    };

    var getContacts = function(provider){
        $loader.show();
        OAuth.popup(provider, {cache: true}).then(function(auth){
            if(provider === 'yahoo'){
                return yahooData(auth);
            } else if (provider === "google") {
                return getGoogleContacts(auth);
            }
        }).then(function(data){
            if(provider === "yahoo"){
                data = getYahooContacts(data);
            }
            return data;
        }).then(function(data){
            if(provider === "yahoo"){
                set_list(parseYahooContacts(data));
            } else if (provider === "google"){
                set_list(parseGoogleContacts(data));
            }
            $loader.hide();
        }).fail(function(err){
            $(".slide-error").html("متاسفانه مشکلی در اتصال به سرویس دهندهٔ مورد نظر رخ داده است.").show();
            console.log(err);
            fadeOutErrorAlert();
            $loader.hide();
        });
    };
    $(".email-yahoo-link").click(function(){
        getContacts("yahoo");
    });
    $(".email-google-link").click(function(){
        getContacts("google");
    });

    $(".email-invite-link").click(function(e){
        e.preventDefault();
        var selects = $('td.check input[type="checkbox"]:checked'),
            result = [];
        for(var i=0; i<selects.length; i++){
            var parent = $(selects[i]).parent().parent(),
                email = parent.find('.email').html(),
                name = parent.find('.name').html();
            result.push({name: name, email: email});
        }
        invite(result);
    });

    // Interaction functions
    var bindTRowClicks = function(){
        $(".emails-list-table > tbody tr").click(function(e){
            var cb = $(this).find(":checkbox")[0];
            e.stopPropagation();
            $(this).find('input[type="checkbox"]').trigger('click');
            $(this).toggleClass('selected', cb.checked);
        });
    };

    $("#checkAll").click(function(e){
        e.stopPropagation();
        $(".emails-list-table > tbody tr.enable input[type='checkbox']").trigger('click');
        $(this).attr("value", $(this).attr("value") === "انتخاب همه" ? "پاک کردن انتخاب‌ها" : "انتخاب همه");
    });

    var resetSelects = function(){
        $(".emails-list-table > tbody tr.enable input[type='checkbox']:checked").map(
            function () {
                return this;
            }).each(
                function(){
                    $(this).click();
                });
        $("#checkAll").attr("value", "انتخاب همه");
    };

    var $table = $('.emails-list-table');
    $table.bind('repaginate', function(){
        $table.find('tbody tr.disable').hide();
        var enableRows = $table.find('tbody tr.enable');
        if(enableRows.length === 0){
            $table.find('tbody #error').show();
            $('#checkAll').attr('disabled', true);
        } else {
            $table.find('tbody #error').hide();
            $('#checkAll').attr('disabled', false);
        }
        pageCount = Math.ceil(enableRows.length / pageLen);
        enableRows.hide().slice(currentPage * pageLen, (currentPage + 1) * pageLen).show();
        currentPage === 0 ? $('#prev-page').hide() : $('#prev-page').show();
        currentPage === pageCount - 1 || pageCount == 0 ? $('#next-page').hide() : $('#next-page').show();
    });

    $("#next-page").click(function(e){
        e.preventDefault();
        currentPage += 1;
        $table.trigger('repaginate');
    });

    $("#prev-page").click(function(e){
        e.preventDefault();
        currentPage -= 1;
        $table.trigger('repaginate');
    });

    var searchField = $('.emails-list-box .table-title .search-friend');
    searchField.bind('change paste keyup', function(){
        // Remove selected items
        resetSelects();
        $('.emails-list-table tr').each(function(){
            var sval = searchField.val();
            var email = $(this).find("td.email").text();
            var name = $(this).find("td.name").text();
            if(email.indexOf(sval) != -1 || name.indexOf(sval) != -1){
                $(this).removeClass('disable').addClass('enable');
            } else {
                $(this).removeClass('enable').addClass('disable');
            }
        });
        currentPage = 0;
        $table.trigger('repaginate');
    });
});
