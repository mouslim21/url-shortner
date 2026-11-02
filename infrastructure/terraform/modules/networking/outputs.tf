output "vpc_id" {
  description = "VPC ID for the application infrastructure."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs for internet-facing infrastructure, in AZ order."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs for future EKS workers, in AZ order."
  value       = aws_subnet.private[*].id
}

output "nat_gateway_id" {
  description = "Single public NAT Gateway ID shared by the private subnets."
  value       = aws_nat_gateway.main.id
}

output "internet_gateway_id" {
  description = "Internet Gateway attached to the VPC."
  value       = aws_internet_gateway.main.id
}

output "vpc_cidr_block" {
  description = "IPv4 CIDR block assigned to the VPC."
  value       = aws_vpc.main.cidr_block
}
