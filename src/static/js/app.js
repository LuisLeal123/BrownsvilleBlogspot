document.addEventListener('DOMContentLoaded', function() {
    const fullGamesList = [ /* your list here */ ];
    let selected = [];
    for (let i = 0; i < 3; i++) {
        const index = Math.floor(Math.random() * fullGamesList.length);
        selected.push(fullGamesList[index]);
        fullGamesList.splice(index, 1); // Remove selected to avoid duplicates
    }

    // Load images and charges in random order
    const charges = [];
    selected.forEach(person => {
        const img = document.createElement('img');
        img.src = person[1];
        img.draggable = false;
        document.getElementById('images').appendChild(img);

        person[2].forEach(charge => charges.push(charge));
    });

    // Shuffle charges
    charges.sort(() => Math.random() - 0.5);

    charges.forEach(charge => {
        const chargeDiv = document.createElement('div');
        chargeDiv.innerText = charge;
        chargeDiv.classList.add('charge');
        chargeDiv.draggable = true;
        chargeDiv.ondragstart = drag;
        document.getElementById('charges').appendChild(chargeDiv);

        const slot = document.createElement('div');
        slot.classList.add('chargeSlot');
        slot.ondrop = drop;
        slot.ondragover = allowDrop;
        document.getElementById('chargeSlots').appendChild(slot);
    });

    function allowDrop(ev) {
        ev.preventDefault();
    }

    function drag(ev) {
        ev.dataTransfer.setData("text", ev.target.id);
    }

    function drop(ev) {
        ev.preventDefault();
        var data = ev.dataTransfer.getData("text");
        ev.target.appendChild(document.getElementById(data));
    }

    window.checkAnswers = function() {
        // Logic to check if charges match the correct person
    };
});
