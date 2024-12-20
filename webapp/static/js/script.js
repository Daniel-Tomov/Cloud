const interval = setInterval(async function () {
    fetch("/web/get_vm_status")
        .then(response => response.json())
        .then(response => {
            if ("logout" in response) {
                clearInterval(interval);
                window.location = "/login";
                return;
            }
            const dict = Object.keys(response);
            var vms_container = document.getElementById("vms_container");
            var cpu, mem, maxmem, netin, netout, status, uptime, tags, child, vm_table, row, cell, box, icon, ip, button = "";

            if (dict.length === 0) {
                vms_container.innerHTML = "";
                button = document.createElement("button");
                button.innerText = "Create VM";
                button.setAttribute("action", "create_vm");
                vms_container.appendChild(button);
                return; 
            }

            var vms_container_temp = document.createElement("div");
            dict.forEach(function (id) {
                vm_table = document.createElement("table");
                vm_table.className = "vm_table";

                row = document.createElement("tr");
                cell = document.createElement("th");
                h1 = document.createElement("h1");
                h1.innerText = response[id]["name"];
                cell.appendChild(h1);
                row.appendChild(cell);
                vm_table.appendChild(row);

                row = document.createElement("tr");

                cell = document.createElement("td");
                cpu = parseFloat(response[id]["cpu"]) * 100;
                cpu = round(cpu, 2);
                append_progress_bar(cell, "cpu_progress", cpu);
                row.appendChild(cell);

                cell = document.createElement("td");
                cpu = "CPU usage: " + cpu + "%";
                append_text_element(cell, "cpu", cpu);
                row.appendChild(cell);

                cell = document.createElement("td");
                if (response[id]["ip"] !== "") {
                    ip = document.createElement("a");
                    ip.className = "ip link"
                    ip.innerText = response[id]["ip"];
                    ip.setAttribute("href", "/?protocol=https&ip=" + response[id]["ip"]) + "&port=8006";
                    cell.appendChild(ip);
                } else if (response[id]["status"] == "running"){
                    ip = document.createElement("p");
                    ip.innerText = "No IP address. Please Wait"
                    cell.appendChild(ip);
                }
                row.appendChild(cell);

                vm_table.appendChild(row);
                row = document.createElement("tr");

                cell = document.createElement("td");
                mem = parseInt(response[id]["mem"]) / Math.pow(1024, 2);
                maxmem = response[id]["maxmem"] / Math.pow(1024, 2)
                append_progress_bar(cell, "mem_progress", (mem / maxmem) * 100);
                row.appendChild(cell);
                cell = document.createElement("td");
                mem = round(mem, 2);
                mem = "Memory usage: " + mem + " MB";
                child = append_text_element(cell, "mem", mem);
                row.appendChild(cell);
                cell = document.createElement("td");
                maxmem = "Maximum memory: " + maxmem + " MB";
                child = append_text_element(cell, "maxmem", maxmem);
                row.appendChild(cell);

                vm_table.appendChild(row);
                row = document.createElement("tr");

                if (response[id]["status"] == "running") {
                    vm_table.className += " running";
                } else {
                    vm_table.className += " stopped";
                }
                cell = document.createElement("td");
                status = "Status: " + response[id]["status"];
                append_text_element(cell, "status", status);
                row.appendChild(cell);

                cell = document.createElement("td");
                netin = parseInt(response[id]["netin"]);
                netin = netin / Math.pow(1024, 2);
                netin = round(netin, 2);
                netin = "Network in: " + netin + " Megabits";
                child = append_text_element(cell, "netin", netin);
                row.appendChild(cell);
                cell = document.createElement("td");
                netout = parseInt(response[id]["netout"]);
                netout = netout / Math.pow(1024, 2);
                netout = round(netout, 2);
                netout = "Network out: " + netout + " Megabits";
                child = append_text_element(cell, "netout", netout);
                row.appendChild(cell);


                vm_table.appendChild(row);
                row = document.createElement("tr");

                
                cell = document.createElement("td");
                box = document.createElement("div");
                box.className = "power-options";

                icon = document.createElement("button");
                icon.className = "fa fa-power-off";
                icon.setAttribute("action", "off");
                icon.setAttribute("vmid", response[id]["id"]);
                icon.setAttribute("node", response[id]["node"]);
                box.appendChild(icon);


                icon = document.createElement("button");
                icon.className = "fa fa-play";
                icon.setAttribute("action", "on");
                icon.setAttribute("vmid", response[id]["id"]);
                icon.setAttribute("node", response[id]["node"]);
                box.appendChild(icon);

                icon = document.createElement("button");
                icon.className = "fa fa-refresh";
                icon.setAttribute("action", "restart");
                icon.setAttribute("vmid", response[id]["id"]);
                icon.setAttribute("node", response[id]["node"]);
                box.appendChild(icon);

                icon = document.createElement("button");
                icon.className = "fa fa-stop";
                icon.setAttribute("action", "stop");
                icon.setAttribute("vmid", response[id]["id"]);
                icon.setAttribute("node", response[id]["node"]);
                box.appendChild(icon);

                cell.appendChild(box);
                row.appendChild(cell);

                cell = document.createElement("td");
                uptime = parseInt(response[id]["uptime"]);
                uptime = uptime / 60 / 60;
                uptime = round(uptime, 2);
                uptime = "Uptime: " + uptime + " Hours";
                append_text_element(cell, "uptime", uptime);
                row.appendChild(cell);

                cell = document.createElement("td");
                append_text_element(cell, "tags", "People with access: ");
                tags = response[id]["tags"];
                tags = tags.split(";");
                tags.forEach(function (t) {
                    child = append_text_element(cell, "tags", t);
                    child.setAttribute("username", t);
                    child.setAttribute("vmid", response[id]["id"]);
                    child.setAttribute("node", response[id]["node"]);
                });
                button = document.createElement("button");
                button.innerText = "Add user";
                button.className = "tag_button";
                button.setAttribute("action", "add_tag");
                button.setAttribute("node", response[id]["node"]);
                button.setAttribute("vmid", response[id]["id"]);
                cell.appendChild(button);


                row.appendChild(cell);

                vm_table.appendChild(row);

                vms_container_temp.appendChild(vm_table);
            })
            vms_container.innerHTML = vms_container_temp.innerHTML;
        })
        .catch(err => console.error(err));

}, 10000);

async function send_power_value(vmid, value, node) {
    await fetch("/web/set_vm_power_state", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            "vmid": vmid,
            "power_value": value,
            "node": node
        })
    }).then(response => {
        if (!response.ok) {
            console.error('Request failed:', response.status, response.statusText);
        }
    }).catch(err => {
        console.error('Network error:', err);
    });
}

async function create_vm(password) {
    await fetch("/web/create_vm", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            "password": password,
        })
    }).then(response => {
        if (!response.ok) {
            console.error('Request failed:', response.status, response.statusText);
        }
    }).catch(err => {
        console.error('Network error:', err);
    });
}

async function send_tag_data(vmid, username, node, add_or_remove) {
    if (add_or_remove === "add" || add_or_remove === "remove") {

        await fetch("/web/" + add_or_remove + "_tag", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                "vmid": vmid,
                "username": username,
                "node": node,
            })
        }).then(response => {
            if (!response.ok) {
                console.error('Request failed:', response.status, response.statusText);
            }
        }).catch(err => {
            console.error('Network error:', err);
        });
    }
}

function append_text_element(parent, class_name, text) {
    var child = document.createElement("p");
    child.className += class_name;
    child.innerText = text;
    parent.appendChild(child)
    return child;
}

function append_progress_bar(parent, class_name, value) {
    var child = document.createElement("progress");
    child.value = value;
    child.max = 100;
    child.className = class_name;
    parent.appendChild(child);
}

function round(num, count) {
    return Math.round(num * Math.pow(10, count)) / Math.pow(10, count);
}

document.getElementById('vms_container').addEventListener('click', function (event) {
    if (event.target.tagName === 'BUTTON') {
        const action = event.target.getAttribute('action');
        const vmId = event.target.getAttribute('vmid');
        const node = event.target.getAttribute('node');

        // Handle different button actions based on button text
        if (action === 'off') {
            send_power_value(vmId, 'shutdown', node);
        } else if (action === 'on') {
            send_power_value(vmId, 'start', node);
        } else if (action === 'restart') {
            send_power_value(vmId, 'reboot', node);
        } else if (action === 'stop') {
            send_power_value(vmId, 'stop', node);
        } else if (action === "add_tag") {
            send_tag_data(vmId, prompt("Enter the MIDAS of the user:"), node, "add");
        } else if (action === "create_vm") {
            create_vm(prompt("Enter the password for the VM:"));
        }
    } else if (event.target.tagName === 'P') {
        const username = event.target.getAttribute('username');
        const vmId = event.target.getAttribute('vmid');
        const node = event.target.getAttribute('node');

        if (username === null || vmId === null) {
            return;
        }
        send_tag_data(vmId, username, node, "remove");
    }
});