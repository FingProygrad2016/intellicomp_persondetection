var current_sources = [];

function publish_log(msg){
    var warnings = $('#warnings');

    var realtop = get_real_scroll_height(warnings.get(0)),
        should_scroll = warnings.get(0).scrollTop == realtop;

    warnings.append(msg);
    if (should_scroll) {
        warnings.animate({scrollTop: warnings.get(0).scrollHeight}, 250);
    }
}

function get_real_scroll_height(the_element){
    tmp = the_element.scrollTop;
    the_element.scrollTop = the_element.scrollHeight;
    realtop = the_element.scrollTop;
    the_element.scrollTop = tmp;

    return realtop;
}

function addConfigInput(parent, item, default_val) {
    var idval = parent + '_' + item,
        idlabel = idval + '_';
    $('#config_values').append(
        '<div class="input-group">' +
        '<span class="input-group-addon" id="' + idlabel + '" title="' +
        idval + '">' + idval.slice(0,20) + '</span>' +
        '<input type="text" value="' + default_val +
        '" class="form-control config_' + parent +
        '" aria-describedby="path_" id="' +
        item + '">' + '</div><br>'
    )
}

log_template_info_image = function(kind, data, image_base64) {
    var formatted_data = '',
        image_block = image_base64 ?
            '<div class="col-md-8" style="text-align: center;">' +
            '<img src="data:image/png;charset=utf-8;base64,' +
            image_base64 + '"></div>' : '',
        text_cols = image_base64 ? '4' : '12';

    _.each(data, function(value, key){
       formatted_data +=  '<b>' + key.toUpperCase() + '</b> ' +
           value + '<br>'
    });

    return '' +
        '<div class="alert alert-' + kind + '" role="alert" style="height: 275px">' +
        '<div class="col-md-' + text_cols + '" style="word-wrap:break-word;">' +
        formatted_data + '</div>' + image_block + '</div>';
};

$('document').ready(function() {

    /*** WEBSOCKET COMMUNICATION ***/

    socket = io.connect('http://' + document.domain + ':' + location.port);

    socket.on('warning', function (msg) {
        var data = JSON.parse(msg.data);
        publish_log(log_template_info_image('danger',
                {'ID': data['tracker_id'],
                'CONFIABILIDAD': data['rules'][0][0],
                'TIPO DE PATRON': data['rules'][0][1]},
                data['img']));
    });
    socket.on('info', function (msg) {
        data = JSON.parse(msg.data);
        if (data.info_id === 'EXIT') {
            remove_source_from_lst(data.id);
            publish_log(log_template_info_image('info',
                {'INFO': data.info_id, 'ID': data.id, 'CONTENT': data.content},
                data.img));
        }else if (data.info_id === 'EXIT WITH ERROR') {
            remove_source_from_lst(data.id);
            publish_log(log_template_info_image('danger',
                {'INFO': data.info_id, 'ID': data.id, 'CONTENT': data.content}));
        }else if (data.info_id === 'SOURCE LIST') {
            _.each(data.content, function(identifier) {
                add_close_source_button(identifier);
                current_sources.push(identifier);
            })
        }else{
            publish_log(log_template_info_image('info',
                {'INFO': data.info_id, 'ID': data.id, 'CONTENT': data.content}));
        }
    });
    socket.on('cmd', function (msg) {
        data = msg.data.split(' ');
        publish_log('<div style="word-wrap: break-word;" ' +
            'class="alert alert-success" role="alert">' +
            msg.data.split(' ').slice(0,4).join(' ') + '</div>');
    });
    socket.on('img', function (msg) {
        publish_log(
            '<div class="alert alert-success" role="alert">' +
            '<img src="data:image/png;charset=utf-8;base64,' +
            msg.data + '"></div>');
    });


    /*** EVENTS ***/

    $(window).unload(function(){
        io.disconnect();
    });

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

    $('#showhide_advancedconf').click(function(e){
       $('#config_values').toggle('slow');
    });

    /*** ASK FOR CURRENT SOURCES RUNNING ***/
    socket.emit('cmd', {
        'data': 'SOURCE LIST'
    });

    /*** LOAD DEFAULT CONFIGS ***/
    $.ajax('/configs').
        done(function(response, status){
            var data = JSON.parse(response)
            _.each(data.trackermaster, function(item){
                addConfigInput('trackermaster', item[0], item[1]);
            }, this);
            _.each(data.patternmaster, function(item){
                addConfigInput('patternmaster', item[0], item[1]);
            }, this);
        }).
        error(alert, 'Couldn\'t load the default configurations.');
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
        var config_trackermaster,
            config_patternmaster;

        function get_config_dict(collection_identifier){
            return _.reduce($(collection_identifier),
                function(partial, new_value){
                    partial[new_value.id] = new_value.value;
                    return partial;
                }, {});
        }

        config_trackermaster = get_config_dict('input.config_trackermaster');
        config_patternmaster = get_config_dict('input.config_patternmaster');

        socket.emit('cmd', {
            'data': 'SOURCE NEW ' +
            btoa(path) + ' ' + btoa(identifier) + ' ' +
            btoa(JSON.stringify(config_trackermaster)) + ' ' +
            btoa(JSON.stringify(config_patternmaster))
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
