$(function(){
    // load url para
    imagesrc = getQueryVariable("objectkey");
    imagesrc = imagesrc.slice(3, -3);   // remove quote
    console.log("cur:", imagesrc)
    imagesrc = "https://sd-visitor-faces.s3.amazonaws.com/" + imagesrc; 
    faceid = getQueryVariable("imageid");
    $('#faceid').val(faceid);
    $('#avatarimg').attr('src', imagesrc);
    $('#modalimg').attr('src', imagesrc);

    //initialize all modals
    $('.modal').modal({
        dismissible: false,
        opacity: 0.85
    });

    //call the specific div (modal)
    $('#modal1').modal('open');

    var textfield = $("input[name=user]");
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

                    const form = document.getElementsByTagName('form')[0];
                    const fromEntries = Object.fromEntries(new FormData(form).entries());
                    // original key: sd-visitors
                    fetch(`${config.apiEndpoint}/wf1`, {
                        method: 'POST',
                        body: JSON.stringify({
                            'message': {
                                faceid: getQueryVariable("imageid"),
                                phonenumber: fromEntries.phonenumber,
                                username: fromEntries.username,
                                photos: {
                                    objectkey:  getQueryVariable("objectkey").slice(3, -3),
                                    bucket:"sd-visitor-faces"
                                }
                            }
                            }),
                        headers: { 'Content-Type': 'image/json' }
                    }).then( data => {
                        if (! data.ok ) {
                            console.log(responseText);
                            M.toast({ html: 'Network error! Please check the log!' });
                        }
                        data.json().then(responseText => {
                            if (responseText.errorMessage != undefined) {
                                console.log(responseText);
                                M.toast({ html: 'Wrong request parameter, please check the log!' });
                            } else {
                                console.log( responseText.body)
                                M.toast({ html: "Success! "+ responseText.body.slice(1, -1) });
                                $("#username").prop( "disabled", true );
                                $("#phonenumber").prop( "disabled", true );
                            }
                        });
                    });

                } else {
                    //remove success mesage replaced with error message
                    $("#output").removeClass(' alert alert-success');
                    $("#output").addClass("alert alert-danger animated fadeInUp").html("sorry enter a username ");
                }
                //console.log(textfield.val());

            });


});


/**
 * Get para from query url.
 */
function getQueryVariable(variable) {
       var query = window.location.search.substring(1);
       var vars = query.split("&");
       for (var i=0;i<vars.length;i++) {
               var pair = vars[i].split("=");
               if(pair[0] == variable){return pair[1];}
       }
       return(false);
}

/**
 * Display button and prompt success.
 */
function blockSuccess() {
    console.log("block him!");
    $("#button-container").html("<h5>You have successfully blocked this user!</h5>");
}


function dumblog() {
    const form = document.getElementsByTagName('form')[0];
    const fromEntries = Object.fromEntries(new FormData(form).entries());
    req = JSON.stringify({
        'message': {
            faceid: getQueryVariable("imageid"),
            phonenumber: fromEntries.phonenumber,
            username: fromEntries.username,
            photos: {
                objectkey:  getQueryVariable("objectkey").slice(3, -3),
                bucket:"sd-visitor-faces"
            }
                }
            });
    console.log(req);
}