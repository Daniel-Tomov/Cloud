document.getElementById('get-data-button').addEventListener('click', function (event) {
    const vmid = document.getElementById("vmid-field").value;
    console.log(vmid);

    fetch("/web/vlan", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            "vmid": vmid
        })
    }).then(response => response.json())
    .then(response => {
        var table = document.createElement("table");
        table.setAttribute("style", "width: 100%");
        var row = document.createElement("tr");

        var cell = document.createElement("td");
        var h2 = document.createElement("h2");
        h2.innerText = response['name'];
        cell.appendChild(h2);
        row.appendChild(cell);

        cell = document.createElement("td");
        h2 = document.createElement("h2");
        h2.innerText = response['node'];
        cell.appendChild(h2);
        row.appendChild(cell);

        table.appendChild(row);

        for (const key in response['nets']) {
            console.log(response['nets'][key]);
            row = document.createElement("tr");
            
            cell = document.createElement("td");
            var p = document.createElement("p");
            p.id = 'mac-' + key;
            p.setAttribute("bridge", response['nets'][key].split(",")[1])
            p.innerText = response['nets'][key].split(",")[0]
            cell.appendChild(p);
            row.appendChild(cell);
            
            cell = document.createElement("td");
            var tag = document.createElement("input");
            tag.name = "tag-" + key
            tag.id = "tag-" + key
            var label = document.createElement("label");
            label.innerText = "Tag: ";
            label.setAttribute("for", "tag-" + key);
            tag.value = response['nets'][key].split("tag=")[1].split(",")[0];
            cell.appendChild(label);
            cell.appendChild(tag);
            row.appendChild(cell);
            
            cell = document.createElement("td");
            var checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.name = "link_down-" + key;
            checkbox.id = "link_down-" + key;
            if (response['nets'][key].includes("link_down=1")) {
                checkbox.checked = false;
            } else {
                checkbox.checked = true;
            }

            var label = document.createElement("label");
            label.innerText = "Connected: ";
            label.setAttribute("for", "link_down-" + key);
            cell.appendChild(label);
            cell.appendChild(checkbox);
            row.appendChild(cell);
            
            cell = document.createElement("td");
            var button = document.createElement("button");
            button.innerText = "Submit";
            
            button.addEventListener("click", function (event) {
                if (document.getElementById("link_down-" + key).checked) {
                    linkDown = '0';
                } else {
                    linkDown = '1';
                }
                fetch("/web/vlan", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        "vmid": vmid, // virtio=BC:24:11:BE:0C:51,bridge=vmbr1,tag=1,link_down=0
                        'data': key + "=" + document.getElementById("mac-" + key).innerText + ',' + document.getElementById("mac-" + key).getAttribute("bridge") + "," + 'tag=' + document.getElementById("tag-" + key).value + ',link_down=' + linkDown
                    })
                })
            });
            cell.appendChild(button);
            row.appendChild(cell);
            
            table.appendChild(row);
        }
        document.getElementById("vm-network-box").innerHTML = "";
        document.getElementById("vm-network-box").appendChild(table);
    })
    .catch(err => {
        console.error('Network error:', err);
    });
});


function submit_vlan_data(netID) {
    console.log(netID);
}