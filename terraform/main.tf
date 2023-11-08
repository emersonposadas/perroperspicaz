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

              # (Additional setup commands can be added here)
              EOF

  tags = {
    Name = "bot-instance"
  }
}
