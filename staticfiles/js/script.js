jQuery(document).ready(function(){
	
	$('#menu-toggle').click(function() {
    if ( $('.the-body').hasClass("open") ) {
			$('.the-body').removeClass('open').delay(300).queue(function(next){
				$('.the-side').hide();
				next();
			});

		} else {
			$('.the-side').show().delay(1).queue(function(next){
				$('.the-body').addClass('open');
				next();
			});
		}
	});

	var eventFired = 0;
	$(window).on('resize', function() {
    if (!eventFired) {
			if ($(window).width() > 768) {
				$('.the-body').addClass('open');
				$('.the-side').show();
			} else {
				$('.the-body').removeClass('open');
				$('.the-side').hide();
			}
    }
	});

});
