var current_sources = [];

function publish_log(msg){
    var warnings = $('#warnings');
    warnings.append(msg);
    warnings.animate({scrollTop: warnings.get(0).scrollHeight}, 500)
}

$('document').ready(function() {


    /*** WEBSOCKET COMMUNICATION ***/

    socket = io.connect('http://' + document.domain + ':' + location.port);

    socket.on('warning', function (msg) {
        data = JSON.parse(msg.data);
        publish_log('<div class="alert alert-danger" role="alert"><b>' +
            data['tracker_id'] + '</b> ' + data['rules'] +
            '<br/><img src="data:image/png;charset=utf-8;base64,' +
            data['img'] + '"</div>');
    });
    socket.on('info', function (msg) {
        data = JSON.parse(msg.data);
        if (data.info_id === 'EXIT') {
            remove_source_from_lst(data.id);
            publish_log('<div style="word-wrap: break-word;" ' +
                'class="alert alert-info" role="alert"><p>EXIT ' +
                data.id + '</p>' + data.content + '</div>');
        }else if (data.info_id === 'EXIT WITH ERROR') {
            remove_source_from_lst(data.id);
            publish_log('<div style="word-wrap: break-word;" ' +
                'class="alert alert-danger" role="alert"><p>EXIT ' +
                data.id + '</p>' + data.content + '</div>');
        }else if (data.info_id === 'SOURCE LIST') {
            _.each(data.content, function(identifier) {
                add_close_source_button(identifier);
                current_sources.push(identifier);
            })
        }else{
            publish_log('<div style="word-wrap: break-word;" ' +
                'class="alert alert-info" role="alert"><p>' + data.info_id +
                ' ' + data.id + '</p>' + data.content + '</div>');
        }
    });
    socket.on('cmd', function (msg) {
        publish_log('<div style="word-wrap: break-word;" ' +
            'class="alert alert-success" role="alert">' +
            msg.data + '</div>');
    });
    socket.on('img', function (msg) {
        publish_log(
            '<div class="alert alert-success" role="alert">' +
            '<img src="data:image/png;charset=utf-8;base64,' +
            msg.data + '"></div>');
    });


    /*** EVENTS ***/

    $('#identifier').keypress(function (e) {
        if (e.which == 13) {
            $('#path').focus();
        }
    });

    $('#path').keypress(function (e) {
        if (e.which == 13) {
            $('#add').trigger('click')
        }
    });

    /*** ASK FOR CURRENT SOURCES RUNNING ***/
    socket.emit('cmd', {
        'data': 'SOURCE LIST'
    });
});

function add_close_source_button(identifier) {
    $('#current_sources').append(
        '<li class="list-group-item list-source-item" >' +
        '<span class="list-source-item-title">' +
        identifier + '</span><button type="button button-md"  ' +
        'style="right: 16px; position: absolute;" ' +
        'class="btn btn-primary btn-md" ' +
        'onclick="remove_source(\'' + identifier + '\')">' +
        'Cerrar</button></li>');
}

function add_new_source() {
    var identifier = $('#identifier');
    var path = $('#path');

    // Input Validations
    var failValidation = false;
    if (_.isEmpty(identifier.val())){
        identifier.parent().addClass('has-error')
        failValidation = true;
    }else{
        identifier.parent().removeClass('has-error')
    }
    if (_.isEmpty(path.val())){
        path.parent().addClass('has-error')
        failValidation = true;
    }else{
        path.parent().removeClass('has-error')
    }
    if(failValidation){
        return false;
    }

    identifier = identifier.val();
    path = path.val();
    if (_.indexOf(current_sources, identifier) === -1) {
        socket.emit('cmd', {
            'data': 'SOURCE NEW ' +
            path + ' ' + identifier
        });
        add_close_source_button(identifier);
        current_sources.push(identifier);
    } else {
        publish_log(
            '<div class="alert alert-danger" role="alert">' +
            'Origen de datos "' + identifier + '" ya está siendo ' +
            'procesado.</div>');
    }
}

function remove_source(identifier) {
    socket.emit('cmd', {'data': 'SOURCE TERMINATE ' + identifier});
    remove_source_from_lst(identifier);
}

function remove_source_from_lst(identifier){
    current_sources = _.without(current_sources, identifier);
    update_sources_list();
}

function update_sources_list() {
    $('#current_sources').html('');
    _.each(current_sources, function (identifier) {
        add_close_source_button(identifier);
    })
}
