import { Component, OnInit } from '@angular/core';
import { FormGroup, FormArray, FormBuilder, FormControl } from '@angular/forms';
import { FabricBuilderService } from 'src/app/services/fabric-builder.service';

@Component({
  selector: 'app-wizard-oob-mgmt',
  templateUrl: './wizard-oob-mgmt.component.html',
  styleUrls: ['./wizard-oob-mgmt.component.scss']
})
export class WizardOOBMgmtComponent implements OnInit {
  oobMgmtForm: FormGroup;

  constructor(private formBuilder: FormBuilder,
              private fabricBuilder: FabricBuilderService) {
    this.oobMgmtForm = this.formBuilder.group({
      config: new FormControl(false),
      v6: new FormControl(false),
      nodes: new FormArray([])
    });
  }

  getFormGroup(groupName): FormGroup {
    return this.oobMgmtForm.get(groupName) as FormGroup;
  }

  getFormArray(groupName: FormGroup, arrayName): FormArray {
    return groupName.get(arrayName) as FormArray;
  }

  newMgmtArray(nodeID) {
    var oobNodes = this.getFormArray(this.oobMgmtForm, 'nodes');

    var newArray = this.formBuilder.group({
      id: [nodeID],
      ipv4Addr: [''],
      ipv4Gw: [''],
      ipv6Addr: [''],
      ipv6Gw: ['']
    });

    oobNodes.push(newArray);
  }

  compareID(a, b) {
    const idA = parseInt(a.id, 10)
    const idB = parseInt(b.id, 10)
  
    let comparison = 0;

    if (idA > idB) {
      comparison = 1;
    } else if (idA < idB) {
      comparison = -1;
    }

    return comparison;
  }

  get formNodes() {
    return <FormArray>this.oobMgmtForm.get('nodes');
  }

  onSubmit() {
    console.log(this.oobMgmtForm.value);
  }

  ngOnInit() {
    var fabricSwitches = this.fabricBuilder.getSwitches();

    fabricSwitches.sort(this.compareID).forEach(sw => {
      if(sw.role != 'controller') {
        this.newMgmtArray(sw.name);
      }
    });
  }
}