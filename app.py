import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import errorcode
import datetime
import streamlit.components.v1 as components
import time

# Custom CSS for background image with transparency and clock styling
st.markdown(
    """
    <style>
        body {
            background-image: url(https://images.pexels.com/photos/3586966/pexels-photo-3586966.jpeg?auto=compress&cs=tinysrgb&w=600);
            background-size: cover;
            background-repeat: no-repeat;
            background-position: center;
            height: 100vh;
            opacity: 0.8;
        }

        .digital-clock {
            position: fixed;
            top: 10px;
            right: 10px;
            font-size: 3.8em; /* Adjusted font size to 1.8em */
            font-weight: bold;
            color: #FFD700; /* Adjusted color to gold */
            z-index: 9999;
            background-color: rgba(0, 0, 0, 0.8); /* Darker background color for better visibility */
            padding: 8px; /* Increased padding for better aesthetics */
            border-radius: 10px; /* Increased border radius for better aesthetics */
            border: 2px solid #FFD700; /* Added border with gold color */
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Live Digital Clock HTML and JavaScript with embedded CSS
digital_clock_html = """
<style>
    .digital-clock {
        position: fixed;
        top: 10px;
        right: 10px;
        font-size: 2.8em;
        font-weight: bold;
        color: #FFD700;
        z-index: 9999;
        background-color: rgba(0, 0, 0, 0.8);
        padding: 10px;
        border-radius: 10px;
        border: 2px solid #FFD700;
    }
</style>

<div class="digital-clock" id="digitalClock"></div>

<script>
function updateDigitalClock() {
    var now = new Date();
    var hours = now.getHours();
    var minutes = now.getMinutes();
    var seconds = now.getSeconds();

    hours = hours < 10 ? "0" + hours : hours;
    minutes = minutes < 10 ? "0" + minutes : minutes;
    seconds = seconds < 10 ? "0" + seconds : seconds;

    var timeString = hours + ":" + minutes + ":" + seconds;
    document.getElementById("digitalClock").innerHTML = timeString;
}

setInterval(updateDigitalClock, 1000);
</script>
"""

# Use st.components.v1.html for better integration
st.components.v1.html(digital_clock_html, height=100, width=200)


# Connect to MySQL database
try:
    connection = mysql.connector.connect(
        host='10.0.0.150',
        port=3306,
        user='Streamlit',
        password='Fpcrxaxams@2023',
        database='Dash',
    )
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        st.error("Error: Access denied. Please check your username and password.")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        st.error("Error: Database does not exist.")
    else:
        st.error(f"Error: {err}")
    st.stop()

# Function to add a new ticket to the database
def add_ticket_to_database(ticket, description, user, site):
    cursor = connection.cursor()

    # Manually generate the ticket number
    cursor.execute('SELECT MAX(Nr) FROM Tickets')
    max_ticket_number = cursor.fetchone()[0]
    next_ticket_number = 1 if max_ticket_number is None else max_ticket_number + 1

    # Set the initial status to 'Open'
    initial_status = 'Open'

    # Insert the data including the 'Time' column with a default value of 0
    cursor.execute('INSERT INTO Tickets (Nr, Ticket, Description, User, Site, Updates, Closed, OpeningTime, ClosingTime, Time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                   (next_ticket_number, ticket, description, user, site, f'Initial status set to {initial_status}', initial_status, None, None, 0))
    connection.commit()
    cursor.close()

# Function to update the status of a ticket in the database
def update_status_in_database(ticket_id, new_status):
    cursor = connection.cursor()

    # Mapping user-friendly status to database-friendly status
    status_mapping = {
        'Open': 'Open',
        'In Progress': 'In Progress',
        'Closed': 'Closed'
    }

    if new_status == 'In Progress':
        # Record the start time when the ticket goes 'In Progress'
        cursor.execute('UPDATE Tickets SET Updates = %s, Closed = %s, OpeningTime = NOW() WHERE Nr = %s',
                       ('Updated status to ' + new_status, status_mapping[new_status], ticket_id))
    elif new_status == 'Closed':
        # Calculate the time difference and update the 'Time' column
        cursor.execute('UPDATE Tickets SET Updates = %s, Closed = %s, ClosingTime = NOW(), Time = REPLACE(SEC_TO_TIME(TIMESTAMPDIFF(SECOND, OpeningTime, NOW())), ":", "-") WHERE Nr = %s',
               ('Updated status to ' + new_status, status_mapping[new_status], ticket_id))
    else:
        # For other statuses, just update the status and updates
        cursor.execute('UPDATE Tickets SET Updates = %s, Closed = %s WHERE Nr = %s',
                       ('Updated status to ' + new_status, status_mapping[new_status], ticket_id))

    connection.commit()
    cursor.close()

# Function to render the "Tickets" page
def tickets_page():
    st.header('Active Tickets')
    
    # Fetch active tickets labeled as 'Open' or 'In Progress'
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM Tickets WHERE Closed IS NULL OR Closed IN (%s, %s)', ('Open', 'In Progress'))
    tickets_data = cursor.fetchall()

    if not tickets_data:
        st.info('No active tickets found.')
    else:
        tickets_df = pd.DataFrame(tickets_data, columns=['Nr', 'Ticket', 'Description', 'User', 'Site', 'Updates', 'Closed', 'Time', 'OpeningTime', 'ClosingTime'])

        # Display the DataFrame with styling
        st.table(tickets_df)

        # Display live digital clock in the top right corner
        current_time = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())  # Get current UTC time
        st.write(f"Database Time: {current_time}")

    cursor.close()


# Function to render the "Create Ticket" page
def create_ticket_page():
    st.header('Create a New Ticket')
    ticket = st.text_input('Ticket:')
    description = st.text_area('Description:')
    user = st.text_input('User:')
    site = st.text_input('Site:')
    if st.button('Create Ticket'):
        if ticket and description and user and site:
            add_ticket_to_database(ticket, description, user, site)
            st.success('Ticket created successfully!')
        else:
            st.warning('Please fill in all the details.')

# Function to render the "View Tickets" page
def view_tickets_page():
    st.header('View All Tickets')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM Tickets')
    tickets_data = cursor.fetchall()

    if not tickets_data:
        st.info('No tickets found.')
    else:
        # Include 'Time' in the list of columns
        tickets_df = pd.DataFrame(tickets_data, columns=['Nr', 'Ticket', 'Description', 'User', 'Site', 'Updates', 'Closed', 'OpeningTime', 'ClosingTime', 'Time'])

        # Define a function to apply styling based on the 'Closed' column
        def highlight_row(row):
            if row['Closed'] == 'Closed':
                return ['background-color: #ffcdd2'] * len(row)  # Lighter shade of red
            elif row['Closed'] == 'Open':
                return ['background-color: #c8e6c9'] * len(row)  # Lighter shade of green
            elif row['Closed'] == 'In Progress':
                return ['background-color: #b3e0ff'] * len(row)  # Lighter shade of blue
            else:
                return [''] * len(row)

        # Apply the styling function to the entire DataFrame
        styled_df = tickets_df.style.apply(highlight_row, axis=1)

        # Display the DataFrame with styling
        st.table(styled_df)

    cursor.close()

# Function to render the "Update Status" page
def update_status_page():
    st.header('Update Ticket Status')

    # Fetch all Ticket IDs and Tickets for the dropdown list
    cursor = connection.cursor()
    cursor.execute('SELECT Nr, Ticket, Closed, OpeningTime, ClosingTime FROM Tickets')  # Removed 'StartTime' from the SELECT clause
    tickets_data = cursor.fetchall()
    ticket_options = {str(ticket[0]): {'Ticket': ticket[1], 'Status': ticket[2], 'OpeningTime': ticket[3], 'ClosingTime': ticket[4]} for ticket in tickets_data}
    cursor.close()

    # Display dropdown for Ticket IDs
    ticket_id = st.selectbox('Select Ticket ID:', list(ticket_options.keys()), format_func=lambda x: ticket_options[x]['Ticket'])

    # Display corresponding Ticket, Status, and Timer
    selected_status = ticket_options[ticket_id]['Status']
    st.text(f'Ticket Status: {selected_status}')

    if selected_status == 'In Progress':
        # Calculate elapsed time and display
        start_time = ticket_options[ticket_id]['OpeningTime']
        elapsed_time = datetime.datetime.now() - start_time if start_time else None
        st.text(f'Elapsed Time: {elapsed_time}')

    new_status = st.selectbox('Select New Status:', ['Open', 'In Progress', 'Closed'])
    if st.button('Update Status'):
        update_status_in_database(int(ticket_id), new_status)
        st.success('Ticket status updated successfully!')

# Streamlit app layout with multiple pages and Tickets tab
def main():
    st.title('Ticketing App')

    # Manage selected tab using st.session_state
    st.session_state.selected_tab = st.sidebar.radio('Navigation', ['Tickets', 'Create Ticket', 'View Tickets', 'Update Status'])

    if st.session_state.selected_tab == 'Tickets':
        tickets_page()
    elif st.session_state.selected_tab == 'Create Ticket':
        create_ticket_page()
    elif st.session_state.selected_tab == 'View Tickets':
        view_tickets_page()
    elif st.session_state.selected_tab == 'Update Status':
        update_status_page()

if __name__ == '__main__':
    main()
