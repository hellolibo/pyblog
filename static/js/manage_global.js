function del(processURL){
	var ids = [], sels = $("input[name=sel_item]:checked");
	if(sels.length){
		sels.each(function(){
			ids.push($(this).val());
		})
		location.href = processURL+ids.join(",");			
	}
	return false;
}