provider "aws" {
  region = "eu-central-1"
}

data "aws_vpc" "default" {
  id = "vpc-1098737a"
}

data "aws_subnet" "default" {
  id = "subnet-a98895e4"
}

resource "aws_security_group" "allow_ssh" {
  name        = "allow_ssh"
  description = "Allow SSH inbound traffic"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Caution: This allows SSH from any IP address, which is not recommended for production environments.
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "allow_ssh"
  }
}

resource "aws_key_pair" "auth" {
  key_name   = "my-key"
  public_key = file("${path.module}/id_rsa.pub")
}

resource "aws_instance" "example" {
  ami                    = "ami-0a485299eeb98b979"
  instance_type          = "t3a.nano"
  key_name               = aws_key_pair.auth.key_name
  subnet_id              = data.aws_subnet.default.id
  vpc_security_group_ids = [aws_security_group.allow_ssh.id]
  associate_public_ip_address = true
  user_data = <<-EOF
              #!/bin/bash
              set -e
              # Update the system
              yum update -y

              # Check for Python 3.11 and install it
              yum install -y python3.11

              # Install pip (if not installed with Python package)
              yum install -y python3-pip

              # Install virtualenv
              python3 -m pip install virtualenv

              # Install required Python packages for the bot
              python3 -m pip install python-telegram-bot aiogram

              # Create a specified user
              export ADMINUSER=foobaruser
              adduser "$ADMINUSER"

              # Add new user to the sudoers file without password prompt
              echo "$ADMINUSER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/"$ADMINUSER"

              # Set up the SSH directory for the user
              mkdir -p /home/"$ADMINUSER"/.ssh
              chmod 700 /home/"$ADMINUSER"/.ssh

              # Replace 'ssh-rsa AAA...' with the public key
              echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCRGXnOAnsm4psKDqHg//OM9UxE4SqbAflOh+QiBQ/uUlXWrAq9oKVgQak+6dPvZv0XpZEA3dF5A5THy5R99Yz28chKnaNAZ1kkQYokRdFM+TlSJMr1SBUxY+JUOc0Neb0vzVlrt3aLC3yKNyhG81mHhDE2C1MDikbBNKBDNb/Napq5bLgeN3up3wve5DnXWVz9UoParw2nnYBP+Dgvp/71u0DHbjAAqkKN5/ErPv76a0z6WWn+F0Geb+jZzXRkAU4ibqEbMfdDZmnITn0eOMcg8pcJ4OiBTqv10Dhnws+PY5y++6b3N6T497PE2GmmftYCEwwKhsUqDLffuRzLaLsV rsa-key-20231107" > /home/chivoberrinches/.ssh/authorized_keys
              chmod 600 /home/"$ADMINUSER"/.ssh/authorized_keys
              chown -R "$ADMINUSER":"$ADMINUSER" /home/"$ADMINUSER"/.ssh

              EOF

  tags = {
    Name = "bot-instance"
  }
}
