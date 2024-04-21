import socket
import subprocess
import time

# MAC: 50:91:E3:0A:C3:72

def find_device():
    # Run the kasa command and capture the output
    command = "kasa --target 10.19.31.255"
    output = subprocess.check_output(command, shell=True, universal_newlines=True)
    print(output)

    # Split the output into lines
    lines = output.split("\n")

    # Flag to track if we are processing the desired device
    processing_device = False

    # Iterate over the lines
    for line in lines:
        # Check if the line contains the device name
        if "MC Energy Monitor" in line:
            processing_device = True
        
        # If we are processing the desired device and the line contains the Host parameter
        if "Host:" in line:
            # Extract the Host parameter value
            host = line.split(":")[1].strip()
            return host

    # If the Host parameter is not found for the desired device
    return None
    

def get_power_reading(ip):
    for _ in range(5):
        try:
            # Run the kasa command with emeter option and capture the output
            command = f"kasa --host {ip} emeter"
            output = subprocess.check_output(command, shell=True, universal_newlines=True)

            # Split the output into lines
            lines = output.split("\n")

            # Initialize the power variable
            power = ""

            # Iterate through the lines
            for line in lines:
                # Check if the line contains the Power value
                if "Power:" in line:
                    power = line.split(":")[1].strip().split(" ")[0]
                    break

            return power
        except Exception as e:
            print(e)
            time.sleep(1)
            continue
    else:
        print("Reading from power device failed")
        return None

def calculate_broadcast_address():
    # Get the IP address of the Raspberry Pi
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)

    # Get the subnet mask using the 'ip' command
    output = subprocess.check_output(['ip', 'addr', 'show', 'dev', 'eth0']).decode('utf-8')
    lines = output.split('\n')
    for line in lines:
        if 'inet ' in line:
            subnet_mask = line.split()[3]
            break

    # Split the IP address and subnet mask into octets
    ip_octets = ip_address.split('.')
    mask_octets = subnet_mask.split('.')

    # Convert octets to integers
    ip_octets = [int(octet) for octet in ip_octets]
    mask_octets = [int(octet) for octet in mask_octets]

    # Calculate the network address
    network_octets = [ip & mask for ip, mask in zip(ip_octets, mask_octets)]

    # Calculate the broadcast address
    broadcast_octets = [network | (255 ^ mask) for network, mask in zip(network_octets, mask_octets)]

    # Convert the broadcast address to string format
    broadcast_address = '.'.join(str(octet) for octet in broadcast_octets)

    return ip_address, subnet_mask, broadcast_address

def _test_energy_read():
    dev = find_device()
    print(dev)
    power = get_power_reading(dev)
    print(f"{power}W")
    return dev, power

if __name__ == "__main__":
    _test_energy_read()
