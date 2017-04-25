 function modify(){
    if($('#file')[0].files.length == 0){
        alert('请先选择文件');
        return false
    }
    var f = $("#filename").value = $("#file")[0].files[0].name;
    var cur = $("#last-guarantee");

    cur.attr("action", cur.attr("action") + f);
    return true
}

function get_device_list(){
    $.get("device_list", function(data){
        var res = $.parseJSON(data);
        var c = 0;
        var his = $.parseJSON($.cookie("device_detail"));
        var state;
        var clr;
        var update = $("#update-file");

        if (res['filename']){
            update.html(res['filename']);
        } else {
            update.html('等待上传');
        }
       
        for (var i in res.device){
            if(his != null){
                if(his[res.device[i]] == 0){
                    state = "未开始";
                    clr = "black";
                } else if(his[res.device[i]] == 1) {
                    state = "已完成";
                    clr = "green";
                } else if(his[res.device[i]] == 2) {
                    state = "失败";
                    clr = "red";
                } else {
                    state = "未开始";
                    clr = "black";
                }
            } else {
                state = "未开始";
                clr = "black";
            }
            $("#device-list").append("<tr><td>" + res.device[i] + "</td><td id='device-" + c
                     + "-result'>" + state + "</td><td><button onclick='update(&quot;device-" + c
                     + "&quot)' data-ip='" + res.device[i] + "' class='btn btn-success' id='device-" + c
                     + "'>开始升级</button>");
            $("#device-" + c + "-result").css("color", clr);

            c += 1;
        }
        if (! window.localStorage){
            console.log("浏览器不支持 localStorage")
        } else {
            localStorage.device_num = c;
        }      

    })
}

function update_all(){
    for(var i=0; i<= localStorage.device_num; i++){
        update("device-" + i);
    }
}

function clear_record(){
    $.cookie("device_detail", null);
    $('.modal').modal();
}

function reload_page(){
    location.reload();
}

function update(id){
    var ip = $("#"+id).data('ip');
    var path = $("#target-path").val();

    $("#" + id + "-result").html('执行中');
    $("#" + id + "-result").css("color","red");
    $("#" + id).attr("disabled", "disabled");

    $.ajax({
        url:"request?device="+ ip +"&path=" + path,
        type: "get",
        timeout: 300000,
        data: {},
        dataType: "json",
        success: function(data){
            var res = $.parseJSON(data);
            var dev_detail = $.parseJSON($.cookie("device_detail"));
            if(dev_detail == null || dev_detail === undefined) {
                dev_detail = new Ojbect();
            }
            if (res.result == 'success'){
                $('#'+ id + '-result').html('已完成');
                $('#'+ id + '-result').css("color", "green");
                $("#" + id).attr("disabled", "");
                
                // cookie device detail, 
                // 1 , 已完成
                // 0 , 未完成
                // 2 , 失败
                // 3 , 超时

                if (dev_detail[res.ip]!= 1) {
                    dev_detail[res.ip] = 1;
                }
                $.cookie("device_detail", JSON.stringify(dev_detail));
                
            } else {
                dev_detail[res.ip] = 2;
                $.cookie("device_detail", JSON.stringify(dev_detail));
                $('#'+ id + '-result').html('失败');
                console.log(res.err);
            }
            return 0
        },
        error: function(data){
            var dev_detail = $.parseJSON($.cookie("device_detail"));
            try{
                var res = $.parseJSON(data.responseText);
            } catch(err){
                if(dev_detail == null || dev_detail === undefined){
                    dev_detail = new Object();
                }
                
                dev_detail[$('#' + id).data('ip')] = 2;
                $.cookie("device_detail", JSON.stringify(dev_detail));
                $('#'+ id + '-result').html('失败');
                console.log('Uncaught exception: ' + err)
                return 1
            }


            if(dev_detail == null || dev_detail === undefined){
                dev_detail = new Object();
            }

            dev_detail[res.ip] = 2;
            $.cookie("device_detail", JSON.stringify(dev_detail));
            $('#'+ id + '-result').html('失败');
            console.log(res.err);
            return 1
        },
        complete: function(XMLHttpRequest, status){
            if(status == 'timeout'){
                console.log('超时');
                $('#'+ id + '-result').html('超时');
            }
        }
    })
}
