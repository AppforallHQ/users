$(function(){    
    $(".planesubmit").click(function(){
        var curr = "<span>تومان</span>"
        $("#show-plane-name .period").text($(this).data('period'))
        $("#show-plane-price").html($(this).data('price')+curr)
        $("#show-promo").html("0"+curr)
        $("#show-payment").html($(this).data('price')+curr)
        
        $(".plane-box").removeClass("active")
        $(this).parent().addClass("active");
        sdata = {'plan' : this.id.replace("planebtn_","")}
        $("#active-plan-value").val(sdata.plan)
        
        
        return false
    })
    $(".plane-box").click(function(){
        $(this).find(".planesubmit").click()
    })
    $("#gt2lvl").click(function(){
        $(".level-body").spin()
        sdata = {'plan' : $("#active-plan-value").val()}
        $.ajax({
            type: 'POST',
            data: sdata,
            url: "/panel/new/"})
        .complete(function(){
            $(".level-body").spin(false)
        })
        .success(function(data) {
            try{
                data = JSON.parse(data)
            }
            catch (e) {
                console.log('JSON ERROR');
            }
            if (data.error) {
              console.log('ERROR');
            }
            else if(data.success) {
                $(".active-line").width("50%")
                $(".level-text.one").removeClass("active")
                $(".level-circle.two").addClass("active")
                $("#slide-1").hide()
                $("#slide-2").fadeIn('slow')
                
                for(var bank in data.active_invoice_payment_url) {
                    $('a#invoice_pay_url_' + bank).attr('href', data.active_invoice_payment_url[bank]);
                }
            }
        })
        .fail(function() {
          console.log('ERROR');
        })
    })
    
    $("#promo_code_enter form").submit(function() {

        $('.level-body').spin()
        $('.slide-error').hide()
    
        $.ajax({
          type: 'POST',
          data: $(this).serialize(),
          url: "/panel/apply_promo/",
          dataType: 'json'
        }).complete(function () {
          $('.level-body').spin(false)
        }).success(function (data) {
          if(data.success){
                $("#promo_code_enter form").hide()
                $("#promo_code_enter .slide-success .partner").html(data.partner)
                $("#promo_code_enter .slide-success .final_price").html(data.final_price)
                $("#promo_code_enter .slide-success").fadeIn()
                
                price = parseInt($("#show-plane-price").text())
                final = parseInt(data.final_price)
                discount = price - final
        
                
                if (final == 0) {
                    $('.banks-logo-box').hide();
                    $('a.invoice_pay_url_free').attr('href', $('a#invoice_pay_url_mellat').attr('href'));
                    $('.hidebankpay').show();
                }
                
                var curr = "<span>تومان</span>"
                $("#show-promo").html(discount+curr)
                $("#show-payment").html(final+curr)
            }
            else{
                $(".slide-error").html(data.message);
                $(".slide-error").fadeIn()    
            }
        }).error(function (xhr) {
            $(".slide-error").fadeIn()
        }).fail(function() {
          console.log('ERROR');
        })
    
        return false;
    });
   $("#planebtn_2").click() 
    
    
   $(".invoice-payment").click(function(){
        $(".payment-gateway").val($(this).data('gateway'))
        $(".payment-form").submit()
        return false
    });
    
    
  $(".logo-box").click(function() {
    if ($("#termsofuse").is(":checked")) {

    } else {        
      $(".termsofuse").addClass("error")
      return false
    }
  });
    
});
