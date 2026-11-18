import {RUN_STATES,SWITCH_STATES} from '../../constants/enums.js';
import {esc} from '../../utils/html.js';
export const badge=value=>`<span class="badge ${esc(value)}">${esc(RUN_STATES[value]||SWITCH_STATES[value]||value)}</span>`;
