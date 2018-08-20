var imgs = {{imdat}};

function changeImage(dir) {
	document.getElementById("demo").innerHTML = 5 + 6;
    var img = document.getElementById("imgClickAndChange");
    img.src = imgs[imgs.indexOf(img.src) + (dir || 1)] || imgs[dir ? imgs.length - 1 : 0];
}

document.onkeydown = function(e) {
	document.getElementById("demo").innerHTML = 5 + 6;
    e = e || window.event;
    if (e.keyCode == '37') {
        changeImage(-1) //left <- show Prev image
    }
    else if (e.keyCode == '39') {
        // right -> show next image
        changeImage()
    }
}