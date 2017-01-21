#!/usr/bin/env bash

# From http://stackoverflow.com/questions/59895/can-a-bash-script-tell-what-directory-its-stored-in
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

if [ -z $LOCAL_ENV_ECLIPSE_PATH ]; then
    LOCAL_ENV_ECLIPSE_PATH=/Applications/Eclipse.app/Contents/MacOS/eclipse
fi

echo "${LOCAL_ENV_ECLIPSE_PATH} at ${DIR}"

${LOCAL_ENV_ECLIPSE_PATH} -data ${DIR} &> /dev/null &

