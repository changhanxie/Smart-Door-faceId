$(function(){
    var textfield = $("input[name=otp]");
    $('button[type="submit"]').click(function(e) {
        e.preventDefault();
                //little validation just to check username
                if (textfield.val() != "") {
                    //$("body").scrollTo("#output");
                    // $("#output").addClass("alert alert-success animated fadeInUp").html("Success");
                    // setTimeout(function(){
                    //     $("#output").removeClass("alert alert-success animated fadeInUp").html("");
                    // }, 3000);


                    const config = {
                        apiEndpoint: 'https://t8ql42inn0.execute-api.us-east-1.amazonaws.com/prod1',
                    };
                    // https://t8ql42inn0.execute-api.us-east-1.amazonaws.com/prod1/wf1

                    const form = document.getElementsByTagName('form')[0];
                    const fromEntries = Object.fromEntries(new FormData(form).entries());
                    // original key: sd-visitors
                    fetch(`${config.apiEndpoint}/wf2`, {
                        method: 'POST',
                        body: JSON.stringify({
                            'message': {
                                faceid: fromEntries.faceid,
                                otp: fromEntries.otp,
                                //phonenumber: fromEntries.phonenumber
                                        //.replace(/[^\d\+]/g, '').replace(/^(?!\+1)/, '+1')
                                    }
                                }),
                        headers: { 'Content-Type': 'image/json' }
                    }).then( data => {
                        if (! data.ok ) {
                            console.log(responseText);
                            M.toast({ html: 'Network error! Please check the log!' });
                        }
                        data.json().then(responseText => {
                            if (responseText.body != "Invalid OTP") {
                                console.log(responseText);
                                window.location.href = "https://visitor-wp2-test.s3.amazonaws.com/greeting.html?name="+responseText.name;
                                // M.toast({ html: 'Wrong request parameter, please check the log!' });
                            } else {
                                console.log("response text:", responseText);
                                window.location.href = "https://visitor-wp2-test.s3.amazonaws.com/error.html";
                                // M.toast({ html: 'Success.' });
                            }
                        });
                    });

                } else {
                    //remove success mesage replaced with error message
                    $("#output").removeClass(' alert alert-success');
                    $("#output").addClass("alert alert-danger animated fadeInUp").html("OTP could not be NULL!");
                    setTimeout(function(){
                        $("#output").removeClass("alert alert-danger animated fadeInUp").html("");
                    }, 3000);
                }
                //console.log(textfield.val());

            });


});
