var fs = require('fs')
var mysql = require('mysql');

var con = mysql.createConnection({
  host: "localhost",
  user: "yourusername",
  password: "yourpassword"
});
var saver = 0

con.connect(function(err) {
  if (err) throw err;
  console.log("Connected!");
  saver = 1
});

var attrs = %s; var args = [];
for (var i = 0; i<attrs.length; i++) {
    args.push(attrs[i] + '=' + Number(cb_obj[attrs[i]]).toFixed(2));
}
var line = "<span style=%r><b>" + cb_obj.event_name + "</b>(" + args.join(", ") + ")</span>\\n";
var text = div.text.concat(line);
var lines = text.split("\\n")
if (lines.length > 35)
    lines.shift();

if (saver==0) div.text = lines.join("\\n");
else div.text = "juchee"