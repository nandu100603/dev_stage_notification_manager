const baseUrl = window.location.origin;
const cont = document.getElementById("coll-container");
const val = document.getElementById('op');
const insert = document.getElementById('insert');
const updateButton = document.getElementById("inserting");
const titleInput = document.getElementById('title')
const messageInput = document.getElementById('message')

document.addEventListener('DOMContentLoaded', function() {
    fetch(`${baseUrl}/templatesfetchfromdb`)
    .then(Response=>{
        if(!Response.ok){
            throw new error('Network response was not ok'+Response.statusText);
        }
        return Response.json();
    })
    .then(templates =>{
        templates.forEach(element => {
            const button = document.createElement('button');
            const button1 = document.createElement('button');
            const content = document.createElement('div');
            const contentText = document.createElement('p')
            const section = document.createElement('div');
            section.className = 'collapsible-section';
            button.className = 'collapsible';
            content.className = 'collapsible-content';
            button1.className = 'delete'
            button.textContent = element.title;
            contentText.textContent = element.message;
            button1.textContent = 'Delete'
            content.appendChild(contentText);
            content.appendChild(button1)
            section.appendChild(button);
            section.appendChild(content);
            cont.appendChild(section)
            button1.disabled = true
            button.addEventListener('click', function(){
                this.classList.toggle('active');
                if (content.style.display === 'block'){
                    content.style.display = 'none'
                } else{
                    content.style.display = 'block'
                }
            });

           button1.addEventListener('click', function(){
            const data = {
                
                template:[
                    {title: element.title, message : element.message}
                ]
            }
            const response = fetch(`${baseUrl}/deletetemplatefromdb`,{
                method: 'DELETE',
                headers:{
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => {
                    if(!response.ok){
                        throw new Error('Network response was not ok '+response.statusText);
                    }
                    return response.json()   
                })
                .then(result=>{
                    section.remove()
                })
                .catch(error=>console.error('error deleting templates ', error))
           }) 
        });
    });



});
async function handleoperationchange(){
    const deleteButtons = document.querySelectorAll('.delete');
    if(val.value === 'new'){
        console.log(val.value)
        insert.style.display = 'block';
        cont.style.display = 'none';
        }
    else if (val.value === 'all'){
        insert.style.display = 'none';
        cont.style.display = 'block';
        deleteButtons.forEach(b=>b.disabled = true)
    }
    else if (val.value === 'remove'){
        insert.style.display = 'none';
        cont.style.display = 'block';
        deleteButtons.forEach(b=>b.disabled = false)

    }
}

async function saveTemplatesJSON(title, message) {
    var newEntry = {
        template: [
            { title: title, message: message }
        ]
    };

    try {
        const response = await fetch(`${baseUrl}/pushtemplatetodb`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(newEntry)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error('Network response was not ok');
        }

        const responseData =await response.json();
        console.log('Success:', responseData);
    } catch (error) {
        console.error('Error:', error);
    }
}

updateButton.addEventListener('click', function() {
    var title =titleInput.value;
    var message = messageInput.value;
    
    var dialogMessage = 'Title: ' + title + '\nMessage: ' + message ;
    var dialog = confirm(dialogMessage);

    if (dialog) {
        
        saveTemplatesJSON(title, message) 
    }
});

fetch(`${baseUrl}/templatesfetchfromdb`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok ' + response.statusText);
            }
            return response.json();
        })
        .then(templates => {
            templates.forEach(template => {
                const option = document.createElement('option');
                option.value = template.title;
                option.textContent = template.title; // Use textContent to set the option's text
                // Truncate message to first 4 words and add "..."
                const truncatedMessage = template.message.split(' ').slice(0, 4).join(' ') + '...';
                option.textContent = `${template.title} | ${truncatedMessage}`;
                templateDropdown.appendChild(option);
            });
        })
        .catch(error => console.error('Error loading final templates:', error));
 
    // Handle dropdown change event
    templateDropdown.addEventListener('change', function() {
        const selectedTitle = this.value;
        if (selectedTitle) {
            fetch(`${baseUrl}/templatesfetchfromdb`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok ' + response.statusText);
                    }
                    return response.json();
                })
                .then(templates => {
                    const selectedTemplate = templates.find(template => template.title === selectedTitle);
                    if (selectedTemplate) {
                        title.value = selectedTemplate.title;
                        message.value = selectedTemplate.message;
                        toggleSendButton(); // Check if send button should be enabled
                    }
                })
                .catch(error => console.error('Error fetching template details:', error));
        } else {
            title.value = '';
            message.value = '';
            toggleSendButton(); // Check if send button should be enabled
        }
    });