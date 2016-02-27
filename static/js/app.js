var current_sources = [];

function publish_log(msg){
    var warnings = $('#warnings');
    warnings.append(msg);
    warnings.animate({scrollTop: warnings.get(0).scrollHeight}, 500)
}

socket = io.connect('http://' + document.domain + ':' + location.port);

socket.on('warning', function (msg) {
    data = JSON.parse(msg.data);
    publish_log('<br><div class="alert alert-danger" role="alert"><b>' +
        data['tracker_id'] + '</b> ' + data['rules'] +
        '<br/><img src="data:image/png;charset=utf-8;base64,' +
        data['img'] + '"</div>');
});
socket.on('info', function (msg) {
    data = JSON.parse(msg.data);
    if (data.info_id === 'EXIT') {
        remove_source_from_lst(data.id);
        publish_log('<br><div style="word-wrap: break-word;" ' +
            'class="alert alert-info" role="alert"><p>EXIT ' +
            data.id + '</p>' + data.img + '</div>');
    }
});
socket.on('cmd', function (msg) {
    publish_log('<br><div style="word-wrap: break-word;" ' +
        'class="alert alert-success" role="alert">' +
        msg.data + '</div>');
});
socket.on('img', function (msg) {
    publish_log(
        '<br><div class="alert alert-success" role="alert">' +
        '<img src="data:image/png;charset=utf-8;base64,' +
        msg.data + '"></div>');
});

function add_close_source_button(identifier) {
    $('#current_sources').append(
        '<li class="list-group-item" style="height: 55px; ' +
        'position: relative;"><span class="" style="float: left;' +
        'word-wrap: break-word;">' +
        identifier + '</span><button type="button button-md"  ' +
        'style="right: 16px; position: absolute;" ' +
        'class="btn btn-primary btn-md" ' +
        'onclick="remove_source(\'' + identifier + '\')">' +
        'Cerrar</button></li>');
}

function add_new_source() {
    var identifier = $('#identifier').val();
    if (_.indexOf(current_sources, identifier) === -1) {
        socket.emit('cmd', {
            'data': 'SOURCE NEW ' +
            $('#path').val() + ' ' + identifier
        });
        add_close_source_button(identifier);
        current_sources.push(identifier);
    } else {
        $('#warnings').append(
            '<br><div class="alert alert-danger" role="alert">' +
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