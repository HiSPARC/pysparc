# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.define "vagrant" do |machine|
    machine.vm.box = "debian/stretch64"
  end

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine. In the example below,
  # accessing "localhost:8080" will access port 80 on the guest machine.
  # config.vm.network "forwarded_port", guest: 80, host: 8080
  config.vm.network "private_network", ip: "192.168.99.20"

  config.vm.synced_folder ".", "/vagrant", type: "virtualbox"

  config.vm.provision "ansible" do |ansible|
    ansible.inventory_path = "provisioning/ansible_inventory"
    ansible.playbook = "provisioning/playbook.yml"
  end
end
