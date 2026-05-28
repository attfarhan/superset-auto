/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import type { CSSProperties } from 'react';
import getOwnerName from 'src/utils/getOwnerName';
import { t } from '@apache-superset/core/translation';
import { Tooltip } from '@superset-ui/core/components';
import type { AuditInfoProps } from './types';

const dateSpanStyle: CSSProperties = {
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  maxWidth: '100%',
  display: 'inline-block',
};

export const ModifiedInfo = ({ user, date }: AuditInfoProps) => {
  const dateSpan = (
    <span style={dateSpanStyle} data-test="audit-info-date">
      {date}
    </span>
  );

  if (user) {
    const userName = getOwnerName(user);
    const title = t('Modified by: %s', userName);
    return (
      <Tooltip title={title} placement="bottom">
        {dateSpan}
      </Tooltip>
    );
  }
  return (
    <Tooltip title={date} placement="bottom">
      {dateSpan}
    </Tooltip>
  );
};

export const CreatedInfo = ({ user, date }: AuditInfoProps) => {
  const dateSpan = (
    <span style={dateSpanStyle} data-test="audit-info-date">
      {date}
    </span>
  );

  if (user) {
    const userName = getOwnerName(user);
    const title = t('Created by: %s', userName);
    return (
      <Tooltip title={title} placement="bottom">
        {dateSpan}
      </Tooltip>
    );
  }
  return (
    <Tooltip title={date} placement="bottom">
      {dateSpan}
    </Tooltip>
  );
};

export type { AuditInfoProps };
